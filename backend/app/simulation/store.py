"""
Agent storage layer: ephemeral (in-memory) and persistent (DB) modes.
MVP uses ephemeral; persistent layer is stubbed for future DB integration.
"""

from typing import Optional, List, Dict
from enum import Enum
import json
import re
import logging
from pathlib import Path
from app.simulation.agent import Agent
from app.simulation.memory import MemorySystem

logger = logging.getLogger(__name__)


class StorageMode(Enum):
    """Storage mode for agents: ephemeral (RAM) or persistent (DB)."""

    EPHEMERAL = "ephemeral"
    PERSISTENT = "persistent"


class AgentStore:
    """
    In-memory agent storage (ephemeral mode).
    Agents stored in RAM; cleared on restart.
    """

    def __init__(self):
        """Initialize ephemeral store."""
        self._agents: Dict[str, Agent] = {}  # agent_id -> Agent
        self._memories: Dict[str, MemorySystem] = {}  # agent_id -> MemorySystem

    def save_agent(self, agent: Agent, memory: Optional[MemorySystem] = None) -> None:
        """Save agent to store. In ephemeral mode, just updates RAM."""
        self._agents[agent.id] = agent
        if memory:
            self._memories[agent.id] = memory

    def load_agent(self, agent_id: str) -> Optional[Agent]:
        """Load agent from store. Returns None if not found."""
        return self._agents.get(agent_id)

    def load_agent_memory(self, agent_id: str) -> Optional[MemorySystem]:
        """Load agent's memory system. Returns None if not found."""
        return self._memories.get(agent_id)

    def delete_agent(self, agent_id: str) -> bool:
        """Delete agent from store. Returns True if deleted, False if not found."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            if agent_id in self._memories:
                del self._memories[agent_id]
            return True
        return False

    def list_agents(
        self, region: Optional[str] = None, role: Optional[str] = None
    ) -> List[Agent]:
        """
        List all agents, optionally filtered by region or role.
        """
        agents = list(self._agents.values())

        if region:
            agents = [a for a in agents if a.region == region]
        if role:
            agents = [a for a in agents if a.role == role]

        return agents

    def get_agent_count(self) -> int:
        """Get total number of agents in store."""
        return len(self._agents)

    def clear_all(self) -> None:
        """Clear all agents (useful for testing or full reset)."""
        self._agents.clear()
        self._memories.clear()


class PersistentAgentStore:
    """
    Persistent agent storage interface (DB-backed).
    STUBBED: Actual DB implementation (SQLite/Postgres) deferred to Phase 4.

    This interface defines the API; implementations will handle:
    - SQLite for single-machine development
    - Postgres for distributed systems
    """

    def __init__(self, db_connection_string: Optional[str] = None):
        """
        Initialize persistent store.

        Args:
            db_connection_string: Connection string (e.g., "sqlite:///agents.db")
        """
        self.db_connection_string = db_connection_string
        # DB initialization would happen here (migrations, schema setup)

    def save_agent(self, agent: Agent, memory: Optional[MemorySystem] = None) -> None:
        """Save agent + memory to database. STUBBED."""
        raise NotImplementedError(
            "Persistent storage not yet implemented. Use ephemeral mode for MVP."
        )

    def load_agent(self, agent_id: str) -> Optional[Agent]:
        """Load agent from database. STUBBED."""
        raise NotImplementedError(
            "Persistent storage not yet implemented. Use ephemeral mode for MVP."
        )

    def load_agent_memory(self, agent_id: str) -> Optional[MemorySystem]:
        """Load agent's memory from database. STUBBED."""
        raise NotImplementedError(
            "Persistent storage not yet implemented. Use ephemeral mode for MVP."
        )

    def delete_agent(self, agent_id: str) -> bool:
        """Delete agent from database. STUBBED."""
        raise NotImplementedError(
            "Persistent storage not yet implemented. Use ephemeral mode for MVP."
        )

    def list_agents(
        self, region: Optional[str] = None, role: Optional[str] = None
    ) -> List[Agent]:
        """List agents from database, optionally filtered. STUBBED."""
        raise NotImplementedError(
            "Persistent storage not yet implemented. Use ephemeral mode for MVP."
        )


class StorageFactory:
    """Factory to create appropriate storage backend based on mode."""

    _store: Optional[AgentStore] = None
    _mode = StorageMode.EPHEMERAL

    @classmethod
    def configure(
        cls, mode: StorageMode = StorageMode.EPHEMERAL, db_url: Optional[str] = None
    ) -> None:
        """
        Configure storage mode.

        Args:
            mode: EPHEMERAL or PERSISTENT
            db_url: Database connection string if using PERSISTENT
        """
        cls._mode = mode

        if mode == StorageMode.EPHEMERAL:
            cls._store = AgentStore()
        elif mode == StorageMode.PERSISTENT:
            # Fall back to ephemeral; persistent not yet implemented
            logger.warning(
                "Persistent storage requested but not yet implemented. Using ephemeral."
            )
            cls._store = AgentStore()

    @classmethod
    def get_store(cls) -> AgentStore:
        """Get the configured storage backend."""
        if cls._store is None:
            cls.configure(StorageMode.EPHEMERAL)
        return cls._store

    @classmethod
    def get_mode(cls) -> StorageMode:
        """Get current storage mode."""
        return cls._mode


# Module-level convenience functions
_default_store: Optional[AgentStore] = None


def init_storage(mode: StorageMode = StorageMode.EPHEMERAL) -> AgentStore:
    """Initialize storage for the application."""
    global _default_store
    StorageFactory.configure(mode)
    _default_store = StorageFactory.get_store()

    # After initializing ephemeral store, let's recover what we can from disk
    if mode == StorageMode.EPHEMERAL:
        recover_agents_from_disk(_default_store)

    return _default_store


def get_storage() -> AgentStore:
    """Get the current storage backend."""
    global _default_store
    if _default_store is None:
        _default_store = init_storage()
    return _default_store


def save_agent(agent: Agent, memory: Optional[MemorySystem] = None) -> None:
    """Save agent to storage."""
    store = get_storage()
    store.save_agent(agent, memory)


def load_agent(agent_id: str) -> Optional[Agent]:
    """Load agent from storage."""
    store = get_storage()
    return store.load_agent(agent_id)


def load_agent_memory(agent_id: str) -> Optional[MemorySystem]:
    """Load agent's memory from storage."""
    store = get_storage()
    return store.load_agent_memory(agent_id)


def list_agents(
    region: Optional[str] = None, role: Optional[str] = None
) -> List[Agent]:
    """List agents from storage."""
    store = get_storage()
    return store.list_agents(region=region, role=role)


def recover_agents_from_disk(store: AgentStore) -> int:
    """
    Scan the agents_data directory to rebuild the in-memory store on restart.
    Parses available metadata.json or extracts metadata by parsing IDENTITY.md.
    """
    agents_dir = Path("agents_data")
    if not agents_dir.exists() or not agents_dir.is_dir():
        return 0

    recovered_count = 0
    from app.simulation.db import get_persona_sections

    for folder in agents_dir.iterdir():
        if not folder.is_dir() or folder.name in ("_unused",):
            continue

        agent_id = folder.name

        # Check if they have a real generated SOUL.md at least
        soul_path = folder / "SOUL.md"
        identity_path = folder / "IDENTITY.md"
        if not soul_path.exists():
            continue

        content = soul_path.read_text()
        if "Generation error" in content or "Generation failed" in content:
            continue

        meta_path = folder / "metadata.json"
        metadata = None

        if meta_path.exists():
            try:
                metadata = json.loads(meta_path.read_text())
            except json.JSONDecodeError:
                pass

        if not metadata and identity_path.exists():
            # Fallback for old agents: parse IDENTITY.md
            id_content = identity_path.read_text()
            metadata = {
                "id": agent_id,
                "name": agent_id,  # Fallback
                "age": 30,
                "ethnicity": "Unknown",
                "region": "Unknown",
                "role": "Agent",
                "role_label": "Job",
                "personality_archetype": "Pragmatist",
            }
            m_name = re.search(r"- Name:\s*(.+)", id_content, re.IGNORECASE)
            if m_name:
                metadata["name"] = m_name.group(1).strip()

            m_age = re.search(r"- Age:\s*(\d+)", id_content, re.IGNORECASE)
            if m_age:
                metadata["age"] = int(m_age.group(1).strip())

            m_eth = re.search(r"- Ethnicity:\s*(.+)", id_content, re.IGNORECASE)
            if m_eth:
                metadata["ethnicity"] = m_eth.group(1).strip()

            m_reg = re.search(r"- Region:\s*(.+)", id_content, re.IGNORECASE)
            if m_reg:
                metadata["region"] = m_reg.group(1).strip()

            m_role = re.search(r"- Role:\s*(.+)", id_content, re.IGNORECASE)
            if m_role:
                metadata["role"] = m_role.group(1).strip()

        if metadata:
            try:
                # Rehydrate using from_disk (skips LLM generation)
                metadata["id"] = agent_id  # Ensure ID is correct
                agent = Agent.from_disk(metadata)

                # Check DB for sections to ensure the DB knows about this agent
                # (Just as a sanity check, though not strictly required for the Agent obj)
                sections = get_persona_sections(agent_id)
                if not sections:
                    # If somehow on disk but missing from DB, we write it to DB
                    from app.simulation.db import (
                        save_persona_section,
                        save_agent_metadata,
                    )

                    save_agent_metadata(
                        agent_id,
                        {
                            "agent_id": agent_id,
                            "sections": [
                                "SOUL",
                                "IDENTITY",
                                "VOICE",
                                "BRAIN",
                                "WORK",
                                "DRIVES",
                            ],
                        },
                    )
                    for section_name in [
                        "SOUL",
                        "IDENTITY",
                        "VOICE",
                        "BRAIN",
                        "WORK",
                        "DRIVES",
                    ]:
                        s_path = folder / f"{section_name}.md"
                        if s_path.exists():
                            save_persona_section(
                                agent_id, section_name, s_path.read_text()
                            )

                # Save into in-memory ephemeral store
                store.save_agent(agent)
                recovered_count += 1
            except Exception as e:
                logger.error(f"Failed to recover agent {agent_id}: {e}")

    logger.info(
        f"Recovered {recovered_count} existing agents from disk into in-memory store."
    )
    return recovered_count
