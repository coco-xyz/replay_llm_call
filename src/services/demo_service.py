"""
Demo Service

Business logic layer for the demo functionality in replay-llm-call.
"""

from typing import Optional

from src.agents import DemoDeps, handle_demo_agent


class DemoService:
    """Demo service for handling agent interactions."""

    async def process_message(
        self, user_message: str, user_name: Optional[str] = None
    ) -> str:
        """
        Process a message with the demo agent.

        Args:
            user_message: User's message
            user_name: Optional user name

        Returns:
            Agent's response
        """
        deps = DemoDeps(user_name=user_name)
        return await handle_demo_agent(user_message, deps=deps)
