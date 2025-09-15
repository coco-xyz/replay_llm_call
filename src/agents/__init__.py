"""
Agents Package

This package contains AI agent instances for the replay-llm-call.
Each agent is defined using pydantic-ai's native Agent syntax.

The demo_agent serves as an example and starting point for building your own agents.
"""

from .demo_agent import DemoDeps, demo_agent, handle_demo_agent

__all__ = ["demo_agent", "DemoDeps", "handle_demo_agent"]
