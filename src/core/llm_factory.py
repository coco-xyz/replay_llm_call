"""
LLM Factory

Simple factory function to create LLM models based on provider and model name.
Also supports creating FallbackModel instances for improved reliability.
"""

from typing import Any, Optional

from pydantic_ai.models import Model
from pydantic_ai.models.fallback import FallbackModel

from .config import settings
from .error_codes import InternalServiceErrorCode
from .exceptions import InternalServiceException


def _extract_secret(secret_str: Any) -> Optional[str]:
    """Safely extract secret value from SecretStr or return None."""
    if secret_str is None:
        return None
    if hasattr(secret_str, "get_secret_value"):
        return str(secret_str.get_secret_value())
    return str(secret_str)


def create_llm_model(model_name: str, provider: str) -> Model:
    """
    Create an LLM model instance based on provider and model name.

    Args:
        model_name (str): Model name, e.g. 'gpt-4o', 'claude-3-5-sonnet'
        provider (str): Provider name ('openai', 'google', 'openrouter', 'anthropic')

    Returns:
        Model: The LLM model instance

    Raises:
        InternalServiceException: If provider is unsupported or model creation fails
    """
    try:
        if provider == "openai":
            return _create_openai_model(model_name)
        elif provider == "google":
            return _create_google_model(model_name)
        elif provider == "openrouter":
            return _create_openrouter_model(model_name)
        elif provider == "anthropic":
            return _create_anthropic_model(model_name)
        else:
            raise InternalServiceException(
                message=f"Unsupported provider: {provider}",
                error_code=InternalServiceErrorCode.OPERATION_FAILED,
                details={
                    "provider": provider,
                    "supported_providers": [
                        "openai",
                        "google",
                        "openrouter",
                        "anthropic",
                    ],
                },
            )
    except InternalServiceException:
        raise
    except Exception as e:
        raise InternalServiceException.wrap(
            e,
            message=f"Failed to create model {model_name} with provider {provider}",
            error_code=InternalServiceErrorCode.OPERATION_FAILED,
            provider=provider,
            model_name=model_name,
        )


def _create_openai_model(model_name: str) -> Model:
    """Create OpenAI model instance."""
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    api_key = _extract_secret(settings.ai__openai_api_key)
    if api_key is None:
        raise InternalServiceException(
            message="OpenAI API key is not configured",
            error_code=InternalServiceErrorCode.OPERATION_FAILED,
            details={"provider": "openai", "model_name": model_name},
        )
    provider = OpenAIProvider(api_key=api_key)
    return OpenAIChatModel(model_name, provider=provider)


def _create_google_model(model_name: str) -> Model:
    """Create Google model instance."""
    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider

    api_key = _extract_secret(settings.ai__google_api_key)
    if api_key is None:
        raise InternalServiceException(
            message="Google API key is not configured",
            error_code=InternalServiceErrorCode.OPERATION_FAILED,
            details={"provider": "google", "model_name": model_name},
        )
    provider = GoogleProvider(api_key=api_key)
    return GoogleModel(model_name, provider=provider)


def _create_openrouter_model(model_name: str) -> Model:
    """Create OpenRouter model instance."""
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openrouter import OpenRouterProvider

    api_key = _extract_secret(settings.ai__openrouter_api_key)
    if api_key is None:
        raise InternalServiceException(
            message="OpenRouter API key is not configured",
            error_code=InternalServiceErrorCode.OPERATION_FAILED,
            details={"provider": "openrouter", "model_name": model_name},
        )
    provider = OpenRouterProvider(api_key=api_key)
    return OpenAIChatModel(model_name, provider=provider)


def _create_anthropic_model(model_name: str) -> Model:
    """Create Anthropic model instance."""
    from pydantic_ai.models.anthropic import AnthropicModel
    from pydantic_ai.providers.anthropic import AnthropicProvider

    api_key = _extract_secret(settings.ai__anthropic_api_key)
    if api_key is None:
        raise InternalServiceException(
            message="Anthropic API key is not configured",
            error_code=InternalServiceErrorCode.OPERATION_FAILED,
            details={"provider": "anthropic", "model_name": model_name},
        )
    provider = AnthropicProvider(api_key=api_key)
    return AnthropicModel(model_name, provider=provider)


def create_fallback_model(primary_model_name: str, primary_provider: str) -> Model:
    """
    Create a FallbackModel instance with primary model and configured fallback model.

    Args:
        primary_model_name (str): Primary model name
        primary_provider (str): Primary provider name

    Returns:
        Model: FallbackModel instance with configured fallback model

    Raises:
        InternalServiceException: If model creation fails
    """
    try:
        # Create primary model
        primary_model = create_llm_model(primary_model_name, primary_provider)

        # Create configured fallback model
        fallback_model = create_llm_model(
            model_name=settings.ai__fallback__model_name,
            provider=settings.ai__fallback__provider,
        )

        # Create FallbackModel with primary and fallback
        return FallbackModel(primary_model, fallback_model)

    except InternalServiceException:
        raise
    except Exception as e:
        raise InternalServiceException.wrap(
            e,
            message=(
                f"Failed to create fallback model {primary_model_name} "
                f"with provider {primary_provider}"
            ),
            error_code=InternalServiceErrorCode.OPERATION_FAILED,
            primary_provider=primary_provider,
            primary_model_name=primary_model_name,
            fallback_provider=settings.ai__fallback__provider,
            fallback_model_name=settings.ai__fallback__model_name,
        )
