"""
Memory system for agents: short-term, long-term, decay, and compression.
Keeps agents coherent across decisions while managing token efficiency.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any


class Memory:
    """Represents a single memory event/fact."""

    def __init__(
        self, content: str, memory_type: str = "event", importance: float = 0.5
    ):
        """
        Initialize a memory.

        Args:
            content: What's being remembered
            memory_type: 'event', 'fact', 'relationship', 'discovery'
            importance: 0-1, how important/salient is this memory?
        """
        self.content = content
        self.memory_type = memory_type
        self.importance = importance
        self.created_at = datetime.now()
        self.last_recalled_at = datetime.now()
        self.recall_count = 0

    def get_recency_weight(self) -> float:
        """
        How recent is this memory?
        Returns 0-1 where 1 is very recent, 0 is very old.
        """
        age_hours = (datetime.now() - self.created_at).total_seconds() / 3600
        # Decay over 7 days (168 hours)
        return max(0, 1 - (age_hours / 168))

    def get_accessibility_weight(self) -> float:
        """
        How accessible is this memory? Frequently recalled memories stand out.
        Returns 0-1.
        """
        return min(1, self.recall_count / 10)  # Cap at 10 recalls

    def get_salience_score(self) -> float:
        """
        Combined score for how "present" this memory is.
        High importance + recent + frequently recalled = very salient.
        """
        recency = self.get_recency_weight() * 0.5
        accessibility = self.get_accessibility_weight() * 0.3
        importance = self.importance * 0.2
        return recency + accessibility + importance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "type": self.memory_type,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "recall_count": self.recall_count,
        }


class MemorySystem:
    """Manages an agent's short-term and long-term memory."""

    def __init__(
        self, agent_id: str, short_term_size: int = 20, long_term_size: int = 100
    ):
        """
        Initialize memory system for an agent.

        Args:
            agent_id: Which agent this memory belongs to
            short_term_size: Max recent memories to keep active
            long_term_size: Max older memories to compress and archive
        """
        self.agent_id = agent_id
        self.short_term_size = short_term_size
        self.long_term_size = long_term_size

        # Short-term: recent, vivid memories (last 20 events)
        self.short_term: List[Memory] = []

        # Long-term: compressed, important memories
        self.long_term: List[Memory] = []

        # Relationship snapshots (compressed)
        self.relationship_notes: Dict[str, str] = {}  # agent_id -> relationship summary

    def remember(
        self, content: str, memory_type: str = "event", importance: float = 0.5
    ) -> None:
        """
        Record a new memory (adds to short-term).
        When short-term fills, old memories are compressed to long-term.
        """
        memory = Memory(content, memory_type, importance)
        self.short_term.append(memory)

        # If short-term is full, compress oldest memories to long-term
        if len(self.short_term) > self.short_term_size:
            self._compress_to_long_term()

    def _compress_to_long_term(self) -> None:
        """
        Move oldest short-term memories to long-term with compression.
        This keeps long-term bounded while preserving important information.
        """
        # Sort short-term by salience; keep top N, compress the rest
        sorted_memories = sorted(
            self.short_term, key=lambda m: m.get_salience_score(), reverse=True
        )

        # Keep top memories in short-term
        self.short_term = sorted_memories[: self.short_term_size]

        # Compress dropped memories into long-term
        compressed = sorted_memories[self.short_term_size :]
        for memory in compressed:
            if len(self.long_term) < self.long_term_size:
                self.long_term.append(memory)

    def recall(self, query: str, top_k: int = 5) -> List[str]:
        """
        Retrieve related memories based on query (simple keyword match + salience).
        Returns top_k most salient matching memories.
        """
        all_memories = self.short_term + self.long_term

        # Score memories by relevance
        scored = []
        for memory in all_memories:
            # Keyword matching (naive but sufficient for MVP)
            query_words = query.lower().split()
            content_lower = memory.content.lower()
            matches = sum(1 for word in query_words if word in content_lower)

            if matches > 0 or memory.get_salience_score() > 0.7:
                score = (matches * 0.4) + (memory.get_salience_score() * 0.6)
                scored.append((memory, score))

        # Sort by score and return top_k
        scored.sort(key=lambda x: x[1], reverse=True)
        retrieved = [mem.content for mem, _ in scored[:top_k]]

        # Mark as recalled (for accessibility weight)
        for mem, _ in scored[:top_k]:
            mem.recall_count += 1
            mem.last_recalled_at = datetime.now()

        return retrieved

    def summarize_for_context(self, max_tokens: int = 200) -> str:
        """
        Generate compressed memory summary for system prompt injection.
        Includes most salient recent events + important learned facts.
        """
        if not self.short_term and not self.long_term:
            return "No significant past memories."

        # Collect most salient memories
        all_memories = self.short_term + self.long_term
        sorted_by_salience = sorted(
            all_memories, key=lambda m: m.get_salience_score(), reverse=True
        )

        # Build summary
        summary_lines = []
        char_count = 0

        for memory in sorted_by_salience[:10]:  # Include top 10 salient memories
            line = f"- {memory.content} ({memory.memory_type})"
            if (
                char_count + len(line) < max_tokens * 4
            ):  # Rough token to char conversion
                summary_lines.append(line)
                char_count += len(line)
            else:
                break

        if summary_lines:
            return "Recent memories:\n" + "\n".join(summary_lines)
        else:
            return "No recent significant memories."

    def add_relationship_note(self, other_agent_id: str, note: str) -> None:
        """Record a compressed note about relationship with another agent."""
        self.relationship_notes[other_agent_id] = note

    def get_relationship_note(self, other_agent_id: str) -> Optional[str]:
        """Retrieve relationship note about another agent."""
        return self.relationship_notes.get(other_agent_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize memory system to dict."""
        return {
            "agent_id": self.agent_id,
            "short_term": [m.to_dict() for m in self.short_term],
            "long_term": [m.to_dict() for m in self.long_term],
            "relationships": self.relationship_notes,
        }

    @staticmethod
    def from_dict(memory_dict: Dict[str, Any]) -> "MemorySystem":
        """Reconstruct memory system from dict."""
        system = MemorySystem(memory_dict.get("agent_id", "unknown"))

        # Restore short-term
        for mem_data in memory_dict.get("short_term", []):
            mem = Memory(mem_data["content"], mem_data["type"], mem_data["importance"])
            mem.recall_count = mem_data["recall_count"]
            system.short_term.append(mem)

        # Restore long-term
        for mem_data in memory_dict.get("long_term", []):
            mem = Memory(mem_data["content"], mem_data["type"], mem_data["importance"])
            mem.recall_count = mem_data["recall_count"]
            system.long_term.append(mem)

        # Restore relationships
        system.relationship_notes = memory_dict.get("relationships", {})

        return system


def create_memory_system(agent_id: str) -> MemorySystem:
    """Public entry point: Create a new memory system for an agent."""
    return MemorySystem(agent_id)
