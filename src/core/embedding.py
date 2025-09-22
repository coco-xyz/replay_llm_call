"""Embedding service for external vector generation.

Provides synchronous and asynchronous helpers to call the Jina embeddings API
with retry support using httpx transports recommended by the pydantic-ai docs.
"""

from __future__ import annotations

from typing import List, Optional

import httpx
from httpx import HTTPStatusError
from pydantic_ai.retries import (
    AsyncTenacityTransport,
    RetryConfig,
    TenacityTransport,
    wait_retry_after,
)
from tenacity import retry_if_exception_type, stop_after_attempt

from src.core.config import create_settings


class JinaEmbeddingClient:
    """Lightweight client for the Jina embeddings endpoint."""

    _SYNC_TIMEOUT = 15.0
    _ASYNC_TIMEOUT = 15.0

    def __init__(self) -> None:
        self._settings = create_settings()
        self._sync_client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None

    @property
    def _api_key(self) -> str:
        secret = self._settings.ai__jina_api_key
        if not secret:
            raise ValueError("Jina API key is not configured")
        if hasattr(secret, "get_secret_value"):
            return str(secret.get_secret_value())
        return str(secret)

    @property
    def _model(self) -> str:
        return self._settings.ai__jina_embeddings__model

    @property
    def _task(self) -> str:
        return self._settings.ai__jina_embeddings__task

    @property
    def _base_url(self) -> str:
        return self._settings.ai__jina_embeddings__base_url

    @property
    def _endpoint_path(self) -> str:
        return "/embeddings"

    def _build_retry_config(self) -> RetryConfig:
        return RetryConfig(
            retry=retry_if_exception_type(HTTPStatusError),
            wait=wait_retry_after(max_wait=120),
            stop=stop_after_attempt(5),
            reraise=True,
        )

    def _get_sync_client(self) -> httpx.Client:
        if self._sync_client is None:
            transport = TenacityTransport(
                config=self._build_retry_config(),
                validate_response=lambda response: response.raise_for_status(),
            )
            self._sync_client = httpx.Client(
                base_url=self._base_url,
                timeout=self._SYNC_TIMEOUT,
                transport=transport,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._sync_client

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            transport = AsyncTenacityTransport(
                config=self._build_retry_config(),
                validate_response=lambda response: response.raise_for_status(),
            )
            self._async_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._ASYNC_TIMEOUT,
                transport=transport,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._async_client

    def embed_text(self, text: str) -> List[float]:
        """Synchronously embed text via the Jina API."""
        payload = {
            "model": self._model,
            "task": self._task,
            "input": [text],
        }
        client = self._get_sync_client()
        response = client.post(self._endpoint_path, json=payload)
        data = response.json()
        try:
            embedding = data["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as exc:  # pragma: no cover - defensive
            raise ValueError("Unexpected embedding response structure") from exc
        return [float(value) for value in embedding]

    async def aembed_text(self, text: str) -> List[float]:
        """Asynchronously embed text via the Jina API."""
        payload = {
            "model": self._model,
            "task": self._task,
            "input": [text],
        }
        client = self._get_async_client()
        response = await client.post(self._endpoint_path, json=payload)
        data = response.json()
        try:
            embedding = data["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError) as exc:  # pragma: no cover - defensive
            raise ValueError("Unexpected embedding response structure") from exc
        return [float(value) for value in embedding]


__all__ = ["JinaEmbeddingClient"]
