"""
Agent class: Represents a single AI agent in the simulation.
Each agent has unique metadata, dynamically generated persona, and mutable state.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from app.services.llm_persona_generator import generate_and_save_persona
from app.services.compiler import compile_agent_prompt


class Agent:
    """A single AI agent with unique identity, persona, and state."""

    def __init__(
        self,
        name: str,
        age: int,
        ethnicity: str,
        region: str,
        role: str,
        role_label: str = "Job",
        personality_archetype: str = "Pragmatist",
        location: Optional[str] = None,
        agent_id: Optional[str] = None,
        skip_generation: bool = False,
    ):
        """
        Initialize an agent with metadata. Persona files are generated on instantiation.

        Args:
            name: Agent's name (string)
            age: Age in years
            ethnicity: Ethnic/cultural background
            region: Geographic region (North America, Europe, etc.)
            role: Profession/occupation (Trader, Farmer, Scholar, etc.)
            role_label: Category of role (Job, Schooling)
            personality_archetype: Personality type (Pragmatist, Guardian, etc.)
            location: Current location string
            agent_id: Optional explicit ID; auto-generated if not provided
        """
        # Immutable metadata
        self.id = agent_id or f"agent_{uuid.uuid4().hex[:12]}"
        self.name = name
        self.age = age
        self.ethnicity = ethnicity
        self.region = region
        self.role = role
        self.role_label = role_label
        self.personality_archetype = personality_archetype

        # Mutable state
        self.location = location or region  # Default to region if not specified
        self.created_at = datetime.now()
        self.last_decision_at: Optional[datetime] = None
        self.current_goal: Optional[str] = None
        self.emotional_state = "neutral"  # neutral, anxious, hopeful, angry, etc.

        # Resources (key-value, domain-specific)
        self.resources: Dict[str, Any] = {
            "gold": 100,  # Default starting currency
            "status": "settled",  # settled, traveling, trading, etc.
        }

        # Relationships (who this agent knows)
        self.relationships: Dict[
            str, Dict[str, Any]
        ] = {}  # agent_id -> {trust, familiarity, ...}

        # Metadata for persona generation
        self._persona_metadata = {
            "name": self.name,
            "age": self.age,
            "ethnicity": self.ethnicity,
            "region": self.region,
            "role": self.role,
            "roleLabel": self.role_label,
            "personality_archetype": self.personality_archetype,
        }

        # Generate persona files dynamically via LLM (unless skipping)
        if not skip_generation:
            self.persona_files = generate_and_save_persona(
                self._persona_metadata, self.id
            )
        else:
            self.persona_files = None

        # Memory (will be injected by memory service)
        self.memory_summary: Optional[str] = None

    @classmethod
    def from_disk(cls, metadata: Dict[str, Any]) -> "Agent":
        """Reconstruct an Agent from saved metadata without calling the LLM."""
        return cls(
            name=metadata.get("name", metadata.get("id", "Unknown")),
            age=metadata.get("age", 30),
            ethnicity=metadata.get("ethnicity", "Unknown"),
            region=metadata.get("region", "Unknown"),
            role=metadata.get("role", "Unknown"),
            role_label=metadata.get("role_label", "Job"),
            personality_archetype=metadata.get("personality_archetype", "Unknown"),
            agent_id=metadata.get("id"),
            skip_generation=True,
        )

    def get_metadata(self) -> Dict[str, Any]:
        """Return immutable metadata about this agent."""
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "ethnicity": self.ethnicity,
            "region": self.region,
            "role": self.role,
            "role_label": self.role_label,
            "personality_archetype": self.personality_archetype,
            "created_at": self.created_at.isoformat(),
        }

    def get_state(self) -> Dict[str, Any]:
        """Return current mutable state of the agent."""
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "current_goal": self.current_goal,
            "emotional_state": self.emotional_state,
            "resources": self.resources,
            "relationships": self.relationships,
            "last_decision_at": self.last_decision_at.isoformat()
            if self.last_decision_at
            else None,
        }

    def compile_system_prompt(
        self, runtime_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Compile this agent's persona + runtime context into system prompt.

        Args:
            runtime_context: Optional runtime state to inject (world, memory, task, etc.)

        Returns:
            Compiled system prompt string
        """
        if runtime_context is None:
            runtime_context = {}

        # Default context if not provided
        default_context = {
            "world": {
                "time": datetime.now().isoformat(),
                "region": self.region,
            },
            "agent": {
                "location": self.location,
                "resources": self.resources,
            },
        }

        # Merge provided context with defaults (provided context takes precedence)
        merged_context = {**default_context, **runtime_context}

        # Inject memory if available
        if self.memory_summary:
            merged_context["memory"] = self.memory_summary

        return compile_agent_prompt(
            persona_files=self.persona_files,
            runtime_context=merged_context,
            agent_id=self.id,
        )

    def get_persona_section(self, section_name: str) -> Optional[str]:
        """Get a specific persona section (SOUL, VOICE, etc.)."""
        file_name = f"{section_name}.md"
        return self.persona_files.get(file_name)

    def update_location(self, new_location: str) -> None:
        """Update agent's location."""
        self.location = new_location

    def update_goal(self, new_goal: str) -> None:
        """Update agent's current goal."""
        self.current_goal = new_goal

    def update_emotional_state(self, state: str) -> None:
        """Update agent's emotional state (neutral, anxious, hopeful, etc.)."""
        self.emotional_state = state

    def update_resources(self, resource_delta: Dict[str, Any]) -> None:
        """Update agent's resources. Delta can be positive or negative."""
        for key, delta in resource_delta.items():
            if key in self.resources:
                if isinstance(self.resources[key], (int, float)):
                    self.resources[key] += delta
                else:
                    self.resources[key] = delta
            else:
                self.resources[key] = delta

    def add_relationship(
        self,
        other_agent_id: str,
        trust_level: float = 0.5,
        familiarity: float = 0.3,
        history: Optional[str] = None,
    ) -> None:
        """
        Create or update relationship with another agent.

        Args:
            other_agent_id: ID of the other agent
            trust_level: 0-1, credibility/reliability perception
            familiarity: 0-1, how well they know each other
            history: Optional string describing history
        """
        self.relationships[other_agent_id] = {
            "trust": trust_level,
            "familiarity": familiarity,
            "history": history or f"Recently met {other_agent_id}",
            "last_interaction": datetime.now().isoformat(),
        }

    def mark_decision_made(self) -> None:
        """Record that agent made a decision (for timestep tracking)."""
        self.last_decision_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize agent to dict (useful for storage)."""
        return {
            "metadata": self.get_metadata(),
            "state": self.get_state(),
            "persona_files": self.persona_files,
            "memory_summary": self.memory_summary,
        }

    @staticmethod
    def from_dict(agent_dict: Dict[str, Any]) -> "Agent":
        """Deserialize agent from dict (reconstruct from storage)."""
        metadata = agent_dict.get("metadata", {})
        state = agent_dict.get("state", {})

        # Reconstruct agent
        agent = Agent(
            name=metadata.get("name", "Unknown"),
            age=metadata.get("age", 30),
            ethnicity=metadata.get("ethnicity", "Mixed"),
            region=metadata.get("region", "Europe"),
            role=metadata.get("role", "Scholar"),
            role_label=metadata.get("role_label", "Job"),
            personality_archetype=metadata.get("personality_archetype", "Pragmatist"),
            location=state.get("location"),
            agent_id=metadata.get("id"),
        )

        # Restore mutable state
        agent.current_goal = state.get("current_goal")
        agent.emotional_state = state.get("emotional_state", "neutral")
        agent.resources = state.get("resources", {})
        agent.relationships = state.get("relationships", {})
        agent.memory_summary = agent_dict.get("memory_summary")

        # Restore persona files (if serialized)
        if "persona_files" in agent_dict:
            agent.persona_files = agent_dict["persona_files"]

        return agent

    def __repr__(self) -> str:
        return f"<Agent {self.name} ({self.role}) at {self.location}>"
