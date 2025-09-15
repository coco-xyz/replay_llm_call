"""
Demo Agent

A simple demonstration agent for the replay-llm-call.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic_ai import Agent

from src.core.llm_registry import get_demo_model


class DemoDeps(BaseModel):
    """Dependencies for the demo agent."""

    user_name: Optional[str] = None


# Create the demo agent
demo_agent = Agent(
    model=get_demo_model(),
    deps_type=DemoDeps,
    system_prompt="You are a helpful AI assistant. Be friendly and concise.",
)


@demo_agent.tool_plain
def get_current_time() -> str:
    """Get the current time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def handle_demo_agent(user_input: str, deps: Optional[DemoDeps] = None) -> str:
    """
    Handle demo agent interaction.

    Args:
        user_input: User's input message
        deps: Optional dependencies for the agent

    Returns:
        Agent's response as a string
    """
    if deps is None:
        deps = DemoDeps()

    try:
        if demo_agent.model is None:
            return (
                f"Demo response to '{user_input}': No LLM configured. "
                "Set up API keys in .env file."
            )

        result = await demo_agent.run(user_input, deps=deps)
        return result.output

    except Exception as e:
        return f"Demo fallback response to '{user_input}': Error occurred - {str(e)}"
