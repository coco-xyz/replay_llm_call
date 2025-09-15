"""
LLM Registry

Business-oriented LLM model registry for replay-llm-call.
Provides easy access to configured AI models with fallback support.

Usage:
    from src.core.llm_registry import get_demo_model, get_default_model

    model = get_demo_model()  # Returns a configured demo model

    # Runtime settings are set during agent.run()
    result = await agent.run(
        "prompt text",
        model_settings={'temperature': 0.1, 'max_tokens': 4000}
    )
"""

from typing import Callable, Dict, Optional

from pydantic_ai.models import Model

from src.core.config import settings
from src.core.llm_factory import (
    create_fallback_model,
    create_llm_model,
)


def get_demo_model() -> Model:
    """
    Get demo model.

    Configuration is read from settings:
    - ai__demo_agent__provider
    - ai__demo_agent__model_name

    Returns:
        Configured demo model instance with fallback support
    """
    return create_fallback_model(
        primary_model_name=settings.ai__demo_agent__model_name,
        primary_provider=settings.ai__demo_agent__provider,
    )


def get_default_model() -> Model:
    """
    Get default model.

    Configuration is read from settings:
    - ai__default_model__provider
    - ai__default_model__name

    Returns:
        Configured default model instance with fallback support
    """
    return create_fallback_model(
        primary_model_name=settings.ai__default_model__name,
        primary_provider=settings.ai__default_model__provider,
    )


def get_fallback_model() -> Model:
    """
    Get fallback model (without additional fallback).

    Configuration is read from settings:
    - ai__fallback__provider
    - ai__fallback__model_name

    Returns:
        Configured fallback model instance (direct, no additional fallback)
    """
    return create_llm_model(
        model_name=settings.ai__fallback__model_name,
        provider=settings.ai__fallback__provider,
    )


def list_available_models() -> Dict[str, Callable[[], Model]]:
    """
    List all available model getters.

    Returns:
        Dictionary of model names and their getter functions
    """
    return {
        "demo": get_demo_model,
        "default": get_default_model,
        "fallback": get_fallback_model,
    }


def get_model_by_name(name: str) -> Optional[Model]:
    """
    Get a model by name.

    Args:
        name: Model name (demo, default, fallback)

    Returns:
        Model instance or None if not found
    """
    models = list_available_models()
    getter = models.get(name)
    return getter() if getter else None
