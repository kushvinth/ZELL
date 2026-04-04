"""
Prompt Compiler: Combines agent persona + runtime context into system prompt.
"""

import json
from typing import Dict, Any, Optional


def compile_agent_prompt(
    persona_files: Dict[str, str],
    runtime_context: Dict[str, Any],
    agent_id: Optional[str] = None,
) -> str:
    """
    Compile agent persona files + runtime context into a system prompt.

    Args:
        persona_files: Dictionary of persona section names to content
                      (e.g., {"SOUL.md": "...", "VOICE.md": "...", ...})
        runtime_context: Dictionary with current world/agent state
                        (world state, agent state, memory, etc.)
        agent_id: Optional agent ID for reference

    Returns:
        Compiled system prompt string combining all sections
    """
    # Start with persona sections concatenated
    system_prompt = "\n\n---\n\n".join(persona_files.values())

    # Add runtime context at the end
    if runtime_context:
        context_str = json.dumps(runtime_context, indent=2)
        system_prompt += f"\n\n# RUNTIME CONTEXT\n{context_str}"

    # Add agent ID reference if provided
    if agent_id:
        system_prompt += f"\n\n# AGENT ID\n{agent_id}"

    return system_prompt
