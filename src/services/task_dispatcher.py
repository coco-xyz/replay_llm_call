"""Task dispatch utilities for background execution.

These abstractions allow the application to swap out the underlying task
execution mechanism (FastAPI background tasks, Celery, etc.) without changing
the service layer.
"""

from fastapi import BackgroundTasks


class RegressionTaskDispatcher:
    """Interface for scheduling regression execution jobs."""

    def dispatch(self, regression_id: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class BackgroundTaskRegressionDispatcher(RegressionTaskDispatcher):
    """Dispatcher that leverages FastAPI BackgroundTasks."""

    def __init__(
        self,
        background_tasks: BackgroundTasks,
        execute_callable,
    ) -> None:
        self._background_tasks = background_tasks
        self._execute_callable = execute_callable

    def dispatch(self, regression_id: str) -> None:
        """Schedule regression execution using FastAPI background tasks."""

        self._background_tasks.add_task(self._execute_callable, regression_id)


__all__ = [
    "RegressionTaskDispatcher",
    "BackgroundTaskRegressionDispatcher",
]
