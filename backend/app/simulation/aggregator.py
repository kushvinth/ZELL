import logging
import random
from typing import List

from app.services.llm import get_llm
from app.simulation.store import load_agent_memory

logger = logging.getLogger(__name__)


async def generate_state_decree(
    region: str, agent_ids: List[str], global_event: str, year: int
) -> str:
    """
    Summarize a sample of local agent reactions into a regional news / state decree.
    """
    llm = get_llm()
    if not llm:
        return f"Rumors spread in {region} regarding {global_event}."

    # Randomly sample up to 10 agents from the region to gauge sentiment
    sample_size = min(10, len(agent_ids))
    sample_agents = random.sample(agent_ids, sample_size)

    sentiments = []
    for aid in sample_agents:
        # Extract last memory
        mem_sys = load_agent_memory(aid)
        if mem_sys and mem_sys.short_term:
            sentiments.append(f"- {mem_sys.short_term[-1].content}")

    if not sentiments:
        return f"The state of {region} issues no formal response to the events."

    context_str = "\n".join(sentiments)

    system_prompt = (
        f"You are a state-level news aggregator acting as the government or mass media "
        f"for the region of {region} in the year {year}."
    )

    user_prompt = (
        f"Global Event: {global_event}\n\n"
        f"Here is a sample of what citizens in your region are saying/doing:\n"
        f"{context_str}\n\n"
        f"Based on this, write a brief (2-3 sentences) official 'State Decree' or 'News Broadcast' "
        f"that reacts to the event and the citizen mood. "
        f"This decree will be broadcast to all citizens."
    )

    try:
        response = llm.generate(
            system_prompt=system_prompt,
            user_message=user_prompt,
            max_tokens=150,
            temperature=0.4,
        )
        return response.strip() if response else "State emergency broadcast."
    except Exception as e:
        logger.error(f"Failed to generate state decree for {region}: {e}")
        return f"State emergency broadcast: The government of {region} is dealing with chaos."
