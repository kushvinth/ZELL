"""
Simulation Orchestrator:
Runs the N-Cycle simulation loop.
Phase A: Intra-human batch generation
Phase B: Gossip Pod mapping
Phase C: State/Macro news aggregation

All agent responses are persisted to the DB and indexed for search.
"""

import asyncio
import logging
import random
import re
from collections import defaultdict
from typing import Dict, Any, List, Optional

from app.simulation.store import list_agents
from app.simulation.executor import execute_agent_decision
from app.simulation.aggregator import generate_state_decree
from app.simulation.memory import create_memory_system
from app.simulation.db import (
    create_simulation_run,
    complete_simulation_run,
    save_agent_response,
    save_agent_relationship,
    save_search_entry,
)
from app.services.search import index_response

logger = logging.getLogger(__name__)


class SimulationOrchestrator:
    def __init__(self, max_concurrent: int = 4):
        self.max_concurrent = max_concurrent
        self.state_news = {}  # region -> str
        self.queue = asyncio.Queue()

        # State tracking
        self.is_running = False
        self.total_cycles = 0
        self.current_cycle = 0
        self.total_agents = 0
        self.completed_agents = 0
        self.current_event = ""
        self.current_run_id: Optional[str] = None
        self._agent_name_map: Dict[str, Dict[str, str]] = {}

    def get_status(self) -> Dict[str, Any]:
        """Return the current progress state of the simulation."""
        return {
            "is_running": self.is_running,
            "total_cycles": self.total_cycles,
            "current_cycle": self.current_cycle,
            "total_agents": self.total_agents,
            "completed_agents": self.completed_agents,
            "current_event": self.current_event,
            "run_id": self.current_run_id,
        }

    async def run_simulation(self, global_event: str, cycles: int, year: int) -> None:
        """Run the full N-cycle global mesh simulation."""
        if self.is_running:
            logger.warning("Simulation is already running!")
            return

        agents = list_agents()
        if not agents:
            logger.warning("No agents available for simulation.")
            return

        self.is_running = True
        self.total_cycles = cycles
        self.total_agents = len(agents)
        self.current_event = global_event
        self.state_news = {}
        self._agent_name_map = {
            a.name.lower(): {"id": a.id, "name": a.name}
            for a in agents
            if getattr(a, "name", None)
        }

        # Create DB run record
        run_id = create_simulation_run(
            event_name=global_event,
            year=year,
            cycles=cycles,
            agent_count=len(agents),
        )
        self.current_run_id = run_id
        logger.info(
            f"Run {run_id}: {cycles}-cycle simulation for {len(agents)} agents. Event: {global_event}"
        )

        try:
            for cycle in range(1, cycles + 1):
                self.current_cycle = cycle
                self.completed_agents = 0
                logger.info(f"--- STARTING CYCLE {cycle}/{cycles} | Run {run_id} ---")

                gossip_by_agent = self._build_gossip_mesh(agents)
                await self._run_decisions_batch(
                    agents, global_event, year, gossip_by_agent, run_id, cycle
                )
                await self._aggregate_state_decrees(agents, global_event, year)

                logger.info(f"--- CYCLE {cycle} COMPLETE ---")

            complete_simulation_run(run_id)
            logger.info(f"Simulation run {run_id} completed.")

        except Exception as e:
            logger.error(f"Simulation error in run {run_id}: {e}")
        finally:
            self.is_running = False

    def _build_gossip_mesh(self, agents: List[Any]) -> Dict[str, str]:
        """Randomly pairs agents in the same region to exchange thoughts (Phase B)."""
        by_region = defaultdict(list)
        for a in agents:
            by_region[a.region].append(a)

        gossip_mesh = {}
        for region, group in by_region.items():
            for a in group:
                if len(group) > 1:
                    peer = random.choice([x for x in group if x.id != a.id])
                    mem = create_memory_system(peer.id)
                    recent = mem.recall(query="*")
                    if recent:
                        gossip_mesh[a.id] = (
                            f"{peer.name} was heard saying/thinking: {recent[0]['content']}"
                        )
                    else:
                        gossip_mesh[a.id] = None
                else:
                    gossip_mesh[a.id] = None

        return gossip_mesh

    async def _run_decisions_batch(
        self,
        agents: List[Any],
        global_event: str,
        year: int,
        gossip_mesh: Dict[str, str],
        run_id: str,
        cycle: int,
    ) -> None:
        """Process agent decisions concurrently, persisting each response."""
        self.queue = asyncio.Queue()

        for agent in agents:
            gossip = gossip_mesh.get(agent.id)
            state_decree = self.state_news.get(agent.region)

            scenario = f"GLOBAL EVENT: {global_event}\n"
            if state_decree:
                scenario += f"STATE BROADCAST: {state_decree}\n"
            if gossip:
                scenario += f"LOCAL RUMOR: {gossip}\n"
            scenario += f"\nYou are in the year {year}. React authentically to these events as the person you are."

            world_state = {
                "time": "midday",
                "season": "current",
                "year": year,
                "region": agent.region,
            }

            self.queue.put_nowait((agent, world_state, scenario, run_id, cycle))

        workers = [
            asyncio.create_task(self._decision_worker())
            for _ in range(self.max_concurrent)
        ]
        await self.queue.join()

        for _ in range(self.max_concurrent):
            self.queue.put_nowait(None)
        await asyncio.gather(*workers)

    async def _decision_worker(self) -> None:
        from app.simulation.store import save_agent

        while True:
            job = await self.queue.get()
            if job is None:
                self.queue.task_done()
                break

            agent, world_state, scenario, run_id, cycle = job
            try:
                memory = create_memory_system(agent.id)
                result = await asyncio.to_thread(
                    execute_agent_decision, agent, memory, world_state, scenario
                )
                await asyncio.to_thread(save_agent, agent, memory)

                # Persist the decision to database
                decision = result.get("decision", {})
                response_id = await asyncio.to_thread(
                    save_agent_response,
                    run_id=run_id,
                    agent_id=agent.id,
                    agent_name=agent.name,
                    agent_role=agent.role,
                    agent_region=agent.region,
                    cycle=cycle,
                    decision=decision,
                )

                # Build searchable text blob and index it
                text_blob = " ".join(
                    filter(
                        None,
                        [
                            decision.get("thoughts", ""),
                            decision.get("plan", ""),
                            decision.get("action", ""),
                            decision.get("migration_intent", ""),
                            decision.get("trust_shift", ""),
                            decision.get("emotional_state", ""),
                        ],
                    )
                )
                if text_blob.strip():
                    # Save to DB search table for persistence across restarts
                    await asyncio.to_thread(
                        save_search_entry, run_id, response_id, agent.id, text_blob
                    )
                    # Index in-memory for fast search
                    index_response(
                        run_id=run_id,
                        response_id=response_id,
                        agent_id=agent.id,
                        agent_name=agent.name,
                        agent_role=agent.role,
                        agent_region=agent.region,
                        cycle=cycle,
                        text_content=text_blob,
                    )

                # Infer graph edges from references to other known agents.
                # This keeps relationship visualization in sync with simulation output.
                inferred = self._infer_relationships(agent, decision)
                for edge in inferred:
                    await asyncio.to_thread(
                        save_agent_relationship,
                        run_id=run_id,
                        source_agent_id=agent.id,
                        source_agent_name=agent.name,
                        target_agent_id=edge["target_agent_id"],
                        target_agent_name=edge["target_agent_name"],
                        relation_type=edge["relation_type"],
                        weight=edge["weight"],
                        context=edge["context"],
                        cycle=cycle,
                    )

                self.completed_agents += 1

            except Exception as e:
                logger.error(f"Decision failed for {agent.name}: {e}")
            finally:
                self.queue.task_done()

    def _infer_relationships(
        self, source_agent: Any, decision: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Infer directed edges by matching known agent names inside narrative text.
        Relation type is classified with lightweight keyword heuristics.
        """
        body = " ".join(
            filter(
                None,
                [
                    decision.get("thoughts", ""),
                    decision.get("action", ""),
                    decision.get("plan", ""),
                    decision.get("migration_intent", ""),
                ],
            )
        ).strip()

        if not body:
            return []

        text = body.lower()
        edges: List[Dict[str, Any]] = []

        for candidate_name, target in self._agent_name_map.items():
            if target["id"] == source_agent.id:
                continue

            pattern = rf"\b{re.escape(candidate_name)}\b"
            matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
            if not matches:
                continue

            mention_count = len(matches)
            relation_type = self._classify_relationship_type(text)
            weight = min(5.0, 1.0 + (mention_count - 1) * 0.6)

            # Capture a short neighborhood around first mention for panel context.
            first = matches[0]
            start = max(0, first.start() - 80)
            end = min(len(body), first.end() + 80)
            context = body[start:end].strip()

            edges.append(
                {
                    "target_agent_id": target["id"],
                    "target_agent_name": target["name"],
                    "relation_type": relation_type,
                    "weight": weight,
                    "context": context,
                }
            )

        return edges

    @staticmethod
    def _classify_relationship_type(text: str) -> str:
        """Classify relationship category from textual cues."""
        conflict_keywords = [
            "threat",
            "fight",
            "against",
            "blame",
            "angry",
            "conflict",
            "oppose",
        ]
        collaborate_keywords = [
            "together",
            "with",
            "coordinate",
            "assist",
            "support",
            "team",
            "ally",
        ]
        influence_keywords = [
            "inspired",
            "persuade",
            "influence",
            "follow",
            "convince",
            "guide",
        ]

        if any(k in text for k in conflict_keywords):
            return "conflicted"
        if any(k in text for k in collaborate_keywords):
            return "collaborated"
        if any(k in text for k in influence_keywords):
            return "influenced"
        return "mentioned"

    async def _aggregate_state_decrees(
        self, agents: List[Any], global_event: str, year: int
    ) -> None:
        """Phase C: Trigger region aggregators concurrently."""
        by_region = defaultdict(list)
        for a in agents:
            by_region[a.region].append(a.id)

        async def _aggregate(region, aids):
            decree = await generate_state_decree(region, aids, global_event, year)
            self.state_news[region] = decree
            logger.info(f"State Decree for {region}: {decree[:80]}...")

        tasks = [_aggregate(reg, aids) for reg, aids in by_region.items()]
        await asyncio.gather(*tasks)


# Global singleton
_orchestrator = None


def get_orchestrator() -> SimulationOrchestrator:
    global _orchestrator
    if not _orchestrator:
        _orchestrator = SimulationOrchestrator()
    return _orchestrator
