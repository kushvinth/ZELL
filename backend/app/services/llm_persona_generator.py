"""
LLM-based persona generator: Creates SOUL, IDENTITY, VOICE, BRAIN, SKILLS, DRIVES
via LLM (Ollama) instead of templates. Stores generated markdown files to disk.
"""

import json
import random
import threading
import os
from pathlib import Path
from typing import Optional, Dict, Any
from app.services.llm import get_llm
import logging

logger = logging.getLogger(__name__)

# Storage location for generated agent markdown files
AGENTS_DATA_DIR = Path(os.getenv("ZELL_AGENTS_DATA_DIR", "agents_data"))
AGENTS_DATA_DIR.mkdir(parents=True, exist_ok=True)

PERSONA_SECTION_NAMES = (
    "SOUL",
    "IDENTITY",
    "VOICE",
    "BRAIN",
    "WORK",
    "DRIVES",
)


class LLMPersonaGenerator:
    """Generates agent personas via LLM instead of hardcoded templates."""

    @staticmethod
    def get_agent_dir(agent_id: str) -> Path:
        """Get or create agent's data directory."""
        agent_dir = AGENTS_DATA_DIR / agent_id
        agent_dir.mkdir(exist_ok=True)
        return agent_dir

    @staticmethod
    def generate_section(
        llm,
        section_name: str,
        agent_metadata: Dict[str, Any],
        previously_generated: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Generate a single persona section via LLM.

        Args:
            llm: LLM service instance
            section_name: SOUL, IDENTITY, VOICE, BRAIN, SKILLS, or DRIVES
            agent_metadata: Agent's base metadata
            previously_generated: Previously generated sections (for context)

        Returns:
            Generated markdown content
        """
        previously_generated = previously_generated or {}

        # Build context from already-generated sections
        context = ""
        if previously_generated:
            context = "\n\nPreviously generated sections:\n"
            for section, content in previously_generated.items():
                context += f"\n## {section}\n{content[:200]}...\n"

        # Section-specific prompts
        prompts = {
            "SOUL": f"""Generate a SOUL.md section for an AI agent with these attributes:
- Name: {agent_metadata.get("name")}
- Age: {agent_metadata.get("age")}
- Personality: {agent_metadata.get("personality_archetype")}
- Role: {agent_metadata.get("role")}
- Region: {agent_metadata.get("region")}
- Ethnicity: {agent_metadata.get("ethnicity")}

The SOUL should define:
- Core identity (who they are)
- Core traits and worldview
- Values and principles
- Moral boundaries
- Decision-making philosophy
- Communication style

Format as markdown with ## headers. Be specific and character-driven.{context}""",
            "IDENTITY": f"""Generate an IDENTITY.md section for an AI agent:
- Name: {agent_metadata.get("name")}
- Age: {agent_metadata.get("age")}
- Ethnicity: {agent_metadata.get("ethnicity")}
- Region: {agent_metadata.get("region")}
- Role: {agent_metadata.get("role")}

Include:
- Static persona metadata (name, age, background, expertise)
- Professional background story
- Current reputation in community
- What drives their daily activities

Format as markdown with ## headers.{context}""",
            "VOICE": f"""Generate a VOICE.md section for an AI agent:
- Name: {agent_metadata.get("name")}
- Region: {agent_metadata.get("region")}
- Personality: {agent_metadata.get("personality_archetype")}

The VOICE should define:
- Linguistic style (precision, complexity)
- Tone and attitude
- Characteristic phrases they use
- Phrases they avoid
- Interaction markers

Format as markdown. Make it distinct and memorable.{context}""",
            "BRAIN": f"""Generate a BRAIN.md section for an AI agent:
- Name: {agent_metadata.get("name")}
- Age: {agent_metadata.get("age")}
- Personality: {agent_metadata.get("personality_archetype")}
- Role: {agent_metadata.get("role")}

Include:
- Thinking model and reasoning approach
- Intellectual tendencies
- Known biases and weaknesses
- How they handle uncertainty
- Decision-making speed preferences

Format as markdown with ## headers.{context}""",
            "WORK": f"""Generate a WORK.md section for an AI agent:
- Name: {agent_metadata.get("name")}
- Role: {agent_metadata.get("role")}
- Age: {agent_metadata.get("age")}

Include:
- Core competencies relevant to their {agent_metadata.get("role")}
- What they're good at
- What they're less good at
- Resources they control
- Depth and nuance of expertise
- Recent professional achievements and daily workflow

Format as markdown. Be realistic about limitations.{context}""",
            "DRIVES": f"""Generate a DRIVES.md section for an AI agent:
- Name: {agent_metadata.get("name")}
- Age: {agent_metadata.get("age")}
- Personality: {agent_metadata.get("personality_archetype")}

Include:
- Core motivations and what moves them
- Anti-patterns (what they avoid)
- What brings meaning to their life
- Fears (even if unspoken)
- Relationship to others

Format as markdown. Make it emotionally grounded.{context}""",
        }

        prompt = prompts.get(section_name, "")
        if not prompt:
            logger.error(f"Unknown section: {section_name}")
            return f"# {section_name}\n\n(Section generation failed)"

        try:
            logger.info(f"Generating {section_name} for agent...")
            response = llm.generate(
                system_prompt=f"You are an expert at creating detailed, consistent character personas. Generate a {section_name} markdown file.",
                user_message=prompt,
                max_tokens=800,
                temperature=0.8,  # Higher creativity for persona generation
            )

            if response:
                # Ensure it starts with markdown header
                if not response.strip().startswith("#"):
                    response = f"# {section_name}\n\n{response}"
                return response
            else:
                logger.warning(f"Empty response for {section_name}")
                return f"# {section_name}\n\n(Generation failed - empty response)"

        except Exception as e:
            logger.error(f"Error generating {section_name}: {e}")
            return f"# {section_name}\n\n(Generation error: {str(e)})"

    @staticmethod
    def generate_full_persona(agent_metadata: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate all 6 persona sections for an agent via LLM.

        Args:
            agent_metadata: Agent metadata (name, age, role, region, etc.)

        Returns:
            Dict of {section_name: markdown_content}
        """
        llm = get_llm()

        sections = {}
        section_order = ["SOUL", "IDENTITY", "VOICE", "BRAIN", "WORK", "DRIVES"]

        logger.info(f"Generating full persona for {agent_metadata.get('name')}...")

        for section in section_order:
            content = LLMPersonaGenerator.generate_section(
                llm,
                section,
                agent_metadata,
                previously_generated=sections,  # Pass context
            )
            sections[section] = content
            logger.debug(f"Generated {section} ({len(content)} chars)")

        return sections

    @staticmethod
    def save_persona_files(
        agent_id: str,
        persona_sections: Dict[str, str],
        agent_metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Save generated persona markdown files to disk, alongside metadata.json.

        Args:
            agent_id: Agent identifier
            persona_sections: Dict of {section_name: content}
            agent_metadata: Full metadata dict to save as metadata.json

        Returns:
            Path to agent directory
        """
        agent_dir = LLMPersonaGenerator.get_agent_dir(agent_id)
        from app.simulation.db import save_persona_section, save_agent_metadata

        # Save metadata to DB
        save_agent_metadata(
            agent_id, {"agent_id": agent_id, "sections": list(persona_sections.keys())}
        )

        for section_name, content in persona_sections.items():
            file_path = agent_dir / f"{section_name}.md"
            with open(file_path, "w") as f:
                f.write(content)

            # Save to DB as requested
            save_persona_section(agent_id, section_name, content)
            logger.info(f"Saved {section_name} for agent {agent_id} to DB and disk")

        # Save metadata.json
        if agent_metadata:
            meta_path = agent_dir / "metadata.json"
            # Ensure an ID exists inside the metadata
            meta_to_save = {**agent_metadata, "id": agent_id}
            with open(meta_path, "w") as f:
                json.dump(meta_to_save, f, indent=2)
            logger.info(f"Saved metadata.json for agent {agent_id}")

        return agent_dir

    @staticmethod
    def load_persona_files(agent_id: str) -> Optional[Dict[str, str]]:
        """
        Load previously generated persona files from disk.

        Args:
            agent_id: Agent identifier

        Returns:
            Dict of {section_name: content} or None if not found
        """
        agent_dir = AGENTS_DATA_DIR / agent_id

        if not agent_dir.exists():
            return None

        sections = {}
        for section_name in ["SOUL", "IDENTITY", "VOICE", "BRAIN", "WORK", "DRIVES"]:
            file_path = agent_dir / f"{section_name}.md"
            if file_path.exists():
                with open(file_path, "r") as f:
                    sections[section_name] = f.read()

        return sections if sections else None

    @staticmethod
    def persona_files_exist(agent_id: str) -> bool:
        """Check if persona files have been generated for agent."""
        agent_dir = AGENTS_DATA_DIR / agent_id
        return (agent_dir / "SOUL.md").exists()


_USED_CORPUS_DIRS = set()
_CORPUS_POOL: Optional[list[Path]] = None
_CORPUS_POOL_LOCK = threading.Lock()


def reset_corpus_cache() -> None:
    """
    Reset in-memory corpus state.

    Call this at the start of each bootstrap/batch run so directory scan
    happens once per run instead of once per agent.
    """
    global _CORPUS_POOL
    with _CORPUS_POOL_LOCK:
        _USED_CORPUS_DIRS.clear()
        _CORPUS_POOL = None


def _build_corpus_pool() -> list[Path]:
    """Scan agents_data once and build eligible cached persona sources."""
    if not AGENTS_DATA_DIR.exists():
        return []

    pool = [
        d
        for d in AGENTS_DATA_DIR.iterdir()
        if d.is_dir()
        and all((d / f"{section}.md").exists() for section in PERSONA_SECTION_NAMES)
    ]
    random.shuffle(pool)
    return pool


def _take_corpus_source(agent_id: str) -> Optional[Path]:
    """Pop one eligible corpus source from the in-memory pool."""
    global _CORPUS_POOL

    with _CORPUS_POOL_LOCK:
        if _CORPUS_POOL is None:
            _CORPUS_POOL = _build_corpus_pool()
            logger.info(
                f"Corpus pool initialized with {len(_CORPUS_POOL)} cached agents"
            )

        while _CORPUS_POOL:
            candidate = _CORPUS_POOL.pop()
            if candidate.name == agent_id:
                continue
            if candidate.name in _USED_CORPUS_DIRS:
                continue

            _USED_CORPUS_DIRS.add(candidate.name)
            _USED_CORPUS_DIRS.add(agent_id)
            return candidate

        _USED_CORPUS_DIRS.add(agent_id)
        return None


def generate_and_save_persona(
    agent_metadata: Dict[str, Any], agent_id: str
) -> Dict[str, str]:
    """
    Public entry point: Generate LLM persona and save to disk.

    Args:
        agent_metadata: Agent metadata
        agent_id: Agent ID

    Returns:
        Dict of generated persona sections
    """
    # Check if this specific agent already has a persona generated
    existing = LLMPersonaGenerator.load_persona_files(agent_id)
    if existing:
        logger.info(f"Persona already exists for {agent_id}, returning cached")
        return existing

    # Attempt to pull from existing corpus to save massive amounts of LLM time
    try:
        chosen_corpus = _take_corpus_source(agent_id)

        # Keep trying corpus candidates before falling back to LLM.
        while chosen_corpus is not None:
            logger.info(f"Retrieving cached from {chosen_corpus.name}")

            sections = {}
            for section_name in PERSONA_SECTION_NAMES:
                file_path = chosen_corpus / f"{section_name}.md"
                if file_path.exists():
                    with open(file_path, "r") as f:
                        sections[section_name] = f.read()

            if len(sections) == len(PERSONA_SECTION_NAMES):
                # Save it to the new agent's slot
                LLMPersonaGenerator.save_persona_files(
                    agent_id, sections, agent_metadata
                )
                return sections

            logger.warning(
                f"Corpus source {chosen_corpus.name} missing required sections; trying another source"
            )
            chosen_corpus = _take_corpus_source(agent_id)

        if chosen_corpus is None:
            logger.info("No unused agents left in corpus. Generating via Ollama...")
    except Exception as e:
        logger.warning(f"Failed to use corpus cache: {e}")

    # Fallback to generating via LLM
    with _CORPUS_POOL_LOCK:
        _USED_CORPUS_DIRS.add(
            agent_id
        )  # Also don't reuse the newly generated one during this batch
    sections = LLMPersonaGenerator.generate_full_persona(agent_metadata)

    # Save to disk
    LLMPersonaGenerator.save_persona_files(agent_id, sections, agent_metadata)

    return sections
