"""
Agent Decision Executor: Orchestrates the perceive → think → act cycle.
Uses LLM to make decisions within agent persona, producing rich narrative outputs.
"""

import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime

from app.simulation.agent import Agent
from app.simulation.memory import MemorySystem
from app.services.llm import get_llm

logger = logging.getLogger(__name__)


class DecisionExecutor:
    """Executes a single decision cycle for an agent."""

    @staticmethod
    def _sanitize_response_text(value: str) -> str:
        """Normalize model text by removing leading quotes and markdown artifacts."""
        if not value:
            return ""

        cleaned = value.strip()

        # Strip leading/trailing quote marks that often leak from generated prose.
        cleaned = re.sub(r'^["\'`“”‘’]+', "", cleaned)
        cleaned = re.sub(r'["\'`“”‘’]+$', "", cleaned)

        # Strip dangling markdown markers from string edges.
        cleaned = re.sub(r"^[*_~`]+", "", cleaned)
        cleaned = re.sub(r"[*_~`]+$", "", cleaned)

        # Remove common markdown formatting syntax while keeping readable text.
        cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"__(.*?)__", r"\1", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"\*(.*?)\*", r"\1", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"_(.*?)_", r"\1", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"`{1,3}([^`]+)`{1,3}", r"\1", cleaned)
        cleaned = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", cleaned)
        cleaned = re.sub(r"^\s*>\s?", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^\s*#{1,6}\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.MULTILINE)

        return cleaned.strip()

    @staticmethod
    def execute_turn(
        agent: Agent,
        memory: MemorySystem,
        world_state: Dict[str, Any],
        scenario_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute one decision cycle: perceive → think → act.

        Returns:
            Decision result with narrative sections, actions, memory updates
        """
        # PERCEIVE: Gather observations
        perception = DecisionExecutor._perceive(agent, memory, world_state)

        # THINK: Use LLM to decide
        decision = DecisionExecutor._think(agent, memory, perception, scenario_prompt)

        # ACT: Update agent state based on decision
        actions = DecisionExecutor._act(agent, memory, decision)

        # Mark decision made
        agent.mark_decision_made()

        return {
            "agent_id": agent.id,
            "agent_name": agent.name,
            "perception": perception,
            "decision": decision,
            "actions": actions,
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def _perceive(
        agent: Agent,
        memory: MemorySystem,
        world_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """PERCEIVE phase: Agent gathers information about current situation."""

        related_memories = memory.recall(
            query=agent.current_goal or agent.role, top_k=5
        )
        memory_summary = memory.summarize_for_context(max_tokens=150)

        runtime_context = {
            "world": {
                "time": world_state.get("time", datetime.now().isoformat()),
                "season": world_state.get("season", "current"),
                "year": world_state.get("year", 2026),
                "region": agent.region,
                "alerts": world_state.get("alerts", []),
            },
            "agent": {
                "location": agent.location,
                "resources": agent.resources,
                "goal": agent.current_goal,
                "emotional_state": agent.emotional_state,
            },
            "memory": memory_summary,
        }

        if world_state.get("nearby_events"):
            runtime_context["world"]["events"] = world_state["nearby_events"][:3]

        return {
            "world_state": runtime_context,
            "recent_memories": related_memories,
            "observables": world_state.get("observables", []),
            "threats": world_state.get("threats", []),
            "opportunities": world_state.get("opportunities", []),
        }

    @staticmethod
    def _think(
        agent: Agent,
        memory: MemorySystem,
        perception: Dict[str, Any],
        scenario_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """THINK phase: Use LLM with agent persona to produce rich narrative decision."""

        try:
            llm = get_llm()

            runtime_context = perception["world_state"]
            system_prompt = DecisionExecutor._build_system_prompt(
                agent, runtime_context
            )
            user_message = DecisionExecutor._build_decision_prompt(
                agent,
                perception,
                scenario_context=scenario_prompt,
            )

            logger.info(
                f"Agent {agent.name} ({agent.role}, {agent.region}) thinking..."
            )
            llm_response = llm.generate(system_prompt, user_message)

            if not llm_response:
                logger.warning(f"Empty LLM response for {agent.name}. Using fallback.")
                return DecisionExecutor._fallback_decision(agent)

            decision = DecisionExecutor._parse_decision(llm_response, agent)
            return decision

        except Exception as e:
            logger.error(f"LLM decision error for {agent.name}: {e}. Using fallback.")
            return DecisionExecutor._fallback_decision(agent)

    @staticmethod
    def _build_system_prompt(agent: Agent, runtime_context: Dict[str, Any]) -> str:
        """Build the system prompt using the agent's compiled persona."""
        try:
            return agent.compile_system_prompt(runtime_context)
        except Exception:
            return (
                f"You are {agent.name}, a {agent.age}-year-old {agent.role} from {agent.region}. "
                f"Your personality: {agent.personality_archetype}. "
                f"You are currently feeling {agent.emotional_state}. "
                f"Respond as this person would — with their specific cultural background, "
                f"profession, fears, and ambitions shaping every thought."
            )

    @staticmethod
    def _build_decision_prompt(
        agent: Agent,
        perception: Dict[str, Any],
        scenario_context: Optional[str] = None,
    ) -> str:
        """
        Build a rich, narrative decision prompt that forces the LLM to reason deeply.

        The agent is asked to produce a stream-of-consciousness response covering:
        - Internal thoughts and emotional reaction
        - Immediate action being taken
        - Longer term plan
        - Whether they intend to migrate (and where)
        - Whether trust changed in a person/product/institution and why
        """
        world = perception["world_state"]["world"]
        agent_ctx = perception["world_state"]["agent"]
        memories = perception.get("recent_memories", [])
        year = world.get("year", 2026)
        region = agent.region
        location = agent_ctx.get("location", region)
        emotional_state = agent_ctx.get("emotional_state", "neutral")
        goal = agent_ctx.get("goal") or f"maintain my life as a {agent.role}"

        memory_lines = ""
        if memories:
            mem_texts = [m.get("content", "") for m in memories[:3] if m.get("content")]
            if mem_texts:
                memory_lines = "Your recent memories:\n" + "\n".join(
                    f"- {t}" for t in mem_texts
                )

        scenario_lines = ""
        if scenario_context:
            scenario_lines = f"EVENT CONTEXT:\n{scenario_context.strip()}\n"

        return f"""
You are {agent.name}, a {agent.age}-year-old {agent.ethnicity} {agent.role} living in {location}, {region}.
It is the year {year}. You are currently feeling {emotional_state}.
Your current focus: {goal}.

{scenario_lines}
{memory_lines}

Something significant has just happened in your world. React to it as a real, complex human being.
Think about how this affects YOUR specific life — your family, your livelihood, your safety, your future.

Formatting rules (critical):
- Write plain text only inside each section.
- Do NOT use markdown emphasis such as *, **, _, __, `, headings, or bullet markers.
- Do NOT wrap your section text in quotation marks.
- Do NOT start THOUGHTS, ACTION, PLAN, MIGRATION_INTENT, or TRUST_SHIFT with a quote character.

Use these headers EXACTLY as shown (including the ## prefix) and write 2-4 sentences under each:

## THOUGHTS
[Your inner monologue — raw, honest, personal. What is running through your mind right now?
How does this event intersect with your specific life circumstances, fears, and hopes?]

## EMOTION
[Single word or short phrase describing your dominant emotional state right now,
followed by one sentence explaining why you feel this way specifically.]

## ACTION
[What are you physically doing RIGHT NOW in response? Be concrete and specific to your role and location.]

## PLAN
[What is your plan for the next days or weeks? Consider your resources, relationships, and obligations.]

## MIGRATION_INTENT
[Are you considering leaving? If yes: where would you go, why that specific place, what obstacles stand in the way?
If no: what keeps you anchored here despite the danger or disruption?]

## TRUST_SHIFT
[Has this event changed your trust in any person, product, company, or institution?
Start the first sentence exactly like this:
CHANGE: increase|decrease|none; TARGET: <name or none>
Then explain the reason from your own lived perspective.]
""".strip()

    @staticmethod
    def _parse_decision(llm_response: str, agent: Agent) -> Dict[str, Any]:
        """
        Parse rich narrative LLM response into structured sections.
        Extracts THOUGHTS, EMOTION, ACTION, PLAN, MIGRATION_INTENT, TRUST_SHIFT blocks.
        """

        def extract_section(text: str, header: str) -> str:
            """Extract text under a ## HEADER section."""
            pattern = rf"##\s*{re.escape(header)}\s*\n(.*?)(?=\n##\s|\Z)"
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
            return ""

        thoughts = extract_section(llm_response, "THOUGHTS")
        emotion = extract_section(llm_response, "EMOTION")
        action = extract_section(llm_response, "ACTION")
        plan = extract_section(llm_response, "PLAN")
        migration_intent = extract_section(llm_response, "MIGRATION_INTENT")
        trust_shift = extract_section(llm_response, "TRUST_SHIFT")

        thoughts = DecisionExecutor._sanitize_response_text(thoughts)
        emotion = DecisionExecutor._sanitize_response_text(emotion)
        action = DecisionExecutor._sanitize_response_text(action)
        plan = DecisionExecutor._sanitize_response_text(plan)
        migration_intent = DecisionExecutor._sanitize_response_text(migration_intent)
        trust_shift = DecisionExecutor._sanitize_response_text(trust_shift)

        # Determine migration flag from content
        migration_lower = migration_intent.lower()
        is_migrating = any(
            word in migration_lower
            for word in [
                "yes",
                "flee",
                "leave",
                "escape",
                "migrate",
                "moving",
                "going to",
                "heading",
            ]
        ) and not any(
            word in migration_lower
            for word in ["not leaving", "staying", "won't leave", "no, i"]
        )

        # Extract migration destination if present
        migration_destination = None
        if is_migrating:
            dest_match = re.search(
                r"(?:to|toward|towards|heading to|moving to|flee to|escape to)\s+([A-Z][a-zA-Z\s,]+?)(?:\.|,|\n|$)",
                migration_intent,
            )
            if dest_match:
                migration_destination = dest_match.group(1).strip()

        trust_change = "none"
        trust_target = None
        if trust_shift:
            change_match = re.search(
                r"change\s*:\s*(increase|decrease|none)", trust_shift, re.IGNORECASE
            )
            if change_match:
                trust_change = change_match.group(1).lower()
            else:
                trust_lower = trust_shift.lower()
                if any(
                    k in trust_lower
                    for k in [
                        "less trust",
                        "trust less",
                        "decrease",
                        "betray",
                        "scam",
                        "lied",
                    ]
                ):
                    trust_change = "decrease"
                elif any(
                    k in trust_lower
                    for k in [
                        "more trust",
                        "trust more",
                        "increase",
                        "restore",
                        "earned trust",
                    ]
                ):
                    trust_change = "increase"

            target_match = re.search(
                r"target\s*:\s*([^\n\.;]+)", trust_shift, re.IGNORECASE
            )
            if target_match:
                candidate = DecisionExecutor._sanitize_response_text(
                    target_match.group(1)
                )
                candidate = re.sub(r"^[\s:;,\.\-]+", "", candidate)
                candidate = re.sub(r"[\s:;,\.\-]+$", "", candidate)
                if candidate and candidate.lower() not in {
                    "none",
                    "n/a",
                    "unknown",
                    "null",
                }:
                    trust_target = candidate

        # Fallback: if parsing fails, use raw lines
        if not action:
            action = f"Continue as {agent.role} amid the unfolding situation"
        if not thoughts:
            thoughts = (
                DecisionExecutor._sanitize_response_text(llm_response)[:300]
                if llm_response
                else f"Processing the situation as a {agent.role}"
            )
        if not emotion:
            emotion = agent.emotional_state or "uncertain"

        # Legacy-compatible fields for old code paths
        return {
            "action": action,
            "reasoning": plan or thoughts,
            "confidence": "high" if thoughts and action else "medium",
            "raw_response": llm_response,
            # Rich narrative fields
            "thoughts": thoughts,
            "emotional_state": emotion,
            "plan": plan,
            "migration_intent": migration_intent,
            "is_migrating": is_migrating,
            "migration_destination": migration_destination,
            "trust_shift": trust_shift,
            "trust_change": trust_change,
            "trust_target": trust_target,
            "is_less_trusting": trust_change == "decrease",
        }

    @staticmethod
    def _fallback_decision(agent: Agent) -> Dict[str, Any]:
        """Fallback decision when LLM fails — still produces structured shape."""
        roles_actions = {
            "Trader": "Scout for trade opportunities in nearby settlements",
            "Farmer": "Tend to fields and check crop health",
            "Scholar": "Study records and teach local community",
            "Warrior": "Train and prepare defenses",
            "Healer": "Prepare medicines and check on patients",
            "Artisan": "Work on current craft project",
            "Administrator": "Review records and organize resources",
        }
        default_action = roles_actions.get(agent.role, "Continue with daily duties")

        return {
            "action": default_action,
            "reasoning": f"Default action for {agent.role} role (LLM unavailable)",
            "confidence": "low",
            "raw_response": "(fallback)",
            "thoughts": f"As a {agent.role} in {agent.region}, I must keep going despite uncertainty.",
            "emotional_state": "uncertain",
            "plan": "Maintain current routine and wait for more information.",
            "migration_intent": "No immediate plans to relocate.",
            "is_migrating": False,
            "migration_destination": None,
            "trust_shift": "CHANGE: none; TARGET: none. I need more verified information before changing trust.",
            "trust_change": "none",
            "trust_target": None,
            "is_less_trusting": False,
        }

    @staticmethod
    def _act(
        agent: Agent,
        memory: MemorySystem,
        decision: Dict[str, Any],
    ) -> Dict[str, Any]:
        """ACT phase: Update agent state and memory based on decision."""

        action = decision.get("action", "")
        confidence = decision.get("confidence", "medium")
        emotional_state = decision.get("emotional_state", "").lower()
        is_migrating = decision.get("is_migrating", False)
        migration_dest = decision.get("migration_destination")

        state_changes = {}

        # Update emotional state from narrative
        if emotional_state:
            simple_emotion = emotional_state.split()[0].split(",")[0].strip()
            agent.update_emotional_state(simple_emotion[:50])
            state_changes["emotional_state"] = simple_emotion

        # Handle migration
        if is_migrating and migration_dest:
            agent.update_location(f"en route to {migration_dest}")
            agent.update_emotional_state("displaced")
            state_changes["location"] = f"en route to {migration_dest}"
            state_changes["migrating"] = True
        else:
            action_lower = action.lower()

            if "trade" in action_lower or "sell" in action_lower:
                if agent.resources.get("gold", 0) > 0:
                    profit = int(agent.resources.get("gold", 0) * 0.1)
                    agent.update_resources({"gold": profit})
                    state_changes["gold_change"] = profit
                agent.update_location("marketplace")

            elif (
                "move" in action_lower
                or "travel" in action_lower
                or "flee" in action_lower
            ):
                agent.update_location("traveling")
                state_changes["location"] = "traveling"

            elif (
                "study" in action_lower
                or "learn" in action_lower
                or "teach" in action_lower
            ):
                state_changes["activity"] = "learning"

            elif (
                "work" in action_lower
                or "tend" in action_lower
                or "craft" in action_lower
            ):
                state_changes["effort_applied"] = True

            elif "train" in action_lower or "defend" in action_lower:
                agent.update_resources(
                    {"preparedness": agent.resources.get("preparedness", 0) + 1}
                )
                state_changes["preparedness_increase"] = True

        # Sample thoughts into memory (store the most important part)
        thoughts_summary = decision.get("thoughts", action)[:200]
        memory.remember(
            content=f"Thought: {thoughts_summary}",
            memory_type="thought",
            importance=0.8,
        )
        memory.remember(
            content=f"Decided: {action} (confidence: {confidence})",
            memory_type="decision",
            importance=0.7 if confidence == "high" else 0.5,
        )

        if state_changes:
            outcome = "; ".join([f"{k}={v}" for k, v in state_changes.items()])
            memory.remember(
                content=f"Action outcome: {outcome}",
                memory_type="event",
                importance=0.6,
            )

        if decision.get("trust_shift"):
            memory.remember(
                content=f"Trust update: {decision.get('trust_shift', '')[:220]}",
                memory_type="reflection",
                importance=0.65,
            )

        return {
            "action_taken": action,
            "state_changes": state_changes,
            "confidence": confidence,
            "agent_state_after": agent.get_state(),
        }


def execute_agent_decision(
    agent: Agent,
    memory: MemorySystem,
    world_state: Dict[str, Any],
    scenario: Optional[str] = None,
) -> Dict[str, Any]:
    """Public entry point: Execute one decision cycle for an agent."""
    executor = DecisionExecutor()
    return executor.execute_turn(agent, memory, world_state, scenario)
