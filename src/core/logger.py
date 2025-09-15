"""
Core Logger Module

Centralized logging configuration for AI Agents project with Logfire integration.
Based on official Logfire documentation best practices.
"""

import logging
import logging.config
import sys
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from src.core.config import settings


def _get_setting(name: str, default: Any) -> Any:
    """Get a setting with a default fallback."""
    return getattr(settings, name, default)


@lru_cache(maxsize=1)
def _get_logfire_module() -> Any:
    """Get cached logfire module or None if not available."""
    try:
        import logfire as _lf

        return _lf
    except Exception:
        return None


def _sanitize_attributes(attrs: Dict[str, Any]) -> Dict[str, Any]:
    """Make record attributes safe for structured logging and redact sensitive keys."""
    safe: Dict[str, Any] = {}
    redact_keywords = ("password", "secret", "token", "api_key", "apikey", "key")
    for k, v in attrs.items():
        lk = k.lower()
        if any(word in lk for word in redact_keywords):
            safe[k] = "<redacted>"
            continue
        try:
            if isinstance(v, (str, int, float, bool)) or v is None:
                safe[k] = v
            else:
                safe[k] = repr(v)
        except Exception:
            safe[k] = "<unserializable>"
    return safe


# Context variable to store session ID for logging
_session_id_context: ContextVar[Optional[str]] = ContextVar("session_id", default=None)


def set_session_id(session_id: str) -> None:
    """Set the session ID in the current context for logging."""
    _session_id_context.set(session_id)


def get_session_id() -> Optional[str]:
    """Get the current session ID from context."""
    return _session_id_context.get()


def clear_session_id() -> None:
    """Clear the session ID from the current context."""
    _session_id_context.set(None)


def get_logfire_with_session() -> Any:
    """
    Get a logfire instance with session ID as tag if available.

    Returns:
        Logfire instance with session tag if session exists,
        default logfire instance if no session,
        or None if logfire not available
    """
    try:
        logfire = _get_logfire_module()
        if logfire is None:
            return None

        session_id = get_session_id()
        if session_id:
            return logfire.with_tags(f"sid:{session_id}")
        return logfire
    except Exception:
        return None


class SessionAwareLogfireHandler(logging.Handler):
    """
    Custom Logfire handler that automatically adds session ID as tag.
    """

    def __init__(
        self,
        level: int = logging.NOTSET,
        fallback: Optional[logging.Handler] = None,
        logfire_instance: Any = None,
    ) -> None:
        super().__init__(level=level)
        self.fallback = fallback or logging.StreamHandler(sys.stderr)
        self.logfire_instance = logfire_instance

    def emit(self, record: logging.LogRecord) -> None:
        """Send the log to Logfire with session tag if available."""
        try:
            # Prefer cached instance if provided
            logfire = self.logfire_instance or _get_logfire_module()
            if logfire is None:
                self.fallback.handle(record)
                return

            # Check if instrumentation is suppressed (best-effort)
            try:
                from opentelemetry.context import get_current
                from opentelemetry.instrumentation.utils import (
                    _SUPPRESS_INSTRUMENTATION_KEY,
                )

                if get_current().get(_SUPPRESS_INSTRUMENTATION_KEY):
                    self.fallback.handle(record)
                    return
            except Exception:
                # If OpenTelemetry is not available or fails, continue with logging
                pass

        except ImportError:
            self.fallback.handle(record)
            return
        except Exception:
            # If we can't check suppression, continue with logging
            pass

        try:
            # Get session ID and create appropriate logfire instance
            session_id = get_session_id()
            if session_id:
                # Only create logfire instance with session tag if session ID exists
                logfire_with_session = logfire.with_tags(f"sid:{session_id}")
            else:
                # Use default logfire instance without any session tags
                logfire_with_session = self.logfire_instance or logfire

            # Prepare attributes from log record
            raw_attrs = {
                k: v
                for k, v in record.__dict__.items()
                if k
                not in [
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "getMessage",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                ]
            }
            attributes = _sanitize_attributes(raw_attrs)

            # Add code location attributes
            attributes["code.filepath"] = record.pathname
            attributes["code.lineno"] = record.lineno
            attributes["code.function"] = record.funcName

            # Format the message
            try:
                msg = record.getMessage()
            except Exception:
                msg = str(record.msg)

            # Send to logfire
            logfire_with_session.log(
                level=record.levelname.lower(),
                msg_template=msg,
                attributes=attributes,
                exc_info=record.exc_info,
            )

        except Exception:
            # Fallback to standard handler if logfire fails
            self.fallback.handle(record)


def get_logging_config() -> Dict[str, Any]:
    """
    Generate logging configuration with Logfire integration.

    Returns:
        Dict: Complete logging configuration dictionary
    """

    # Determine log level
    log_level = (_get_setting("log_level", "info") or "info").upper()

    # Create logs directory for fallback (configurable)
    logs_dir = Path(_get_setting("log__dir", "logs"))
    logs_dir.mkdir(exist_ok=True)

    # Determine file path - use custom path if provided, otherwise use dir + default filename
    file_path = _get_setting("log__file_path", None)
    if file_path is None:
        file_path = str(logs_dir / "replay_llm_call.log")

    # Base handlers - always include console and file for fallback
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "simple",
            "stream": sys.stdout,
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": _get_setting("log__file_level", "INFO"),
            "formatter": "detailed",
            "filename": file_path,
            "maxBytes": int(_get_setting("log__file_max_bytes", 10 * 1024 * 1024)),
            "backupCount": int(_get_setting("log__file_backup_count", 3)),
            "encoding": "utf-8",
        },
    }

    # Configure Logfire handler if enabled (added later via setup_logfire_handler)
    if _get_setting("logfire__enabled", False):
        pass

    # Base configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": handlers,
        "loggers": {
            # replay-llm-call application loggers
            "replay_llm_call": {
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            # Third-party library loggers - reduce verbosity but keep important logs
            "uvicorn.access": {"level": "WARNING", "propagate": True},
            "httpx": {"level": "WARNING", "propagate": True},
            "urllib3": {"level": "WARNING", "propagate": True},
        },
        "root": {"level": "WARNING", "handlers": ["console"]},
    }

    return config


def setup_logfire_handler() -> None:
    """
    Set up Logfire handler after logfire.configure() has been called.
    This should be called from main.py after Logfire is configured.
    """

    if not _get_setting("logfire__enabled", False):
        return

    try:
        logfire = _get_logfire_module()
        if logfire is None:
            return

        # Create fallback handler with urllib3 filtering
        fallback_handler = logging.StreamHandler(sys.stderr)
        fallback_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

        # Filter out urllib3 debug logs from fallback handler
        urllib3_filter = logging.Filter("urllib3")
        fallback_handler.addFilter(lambda record: not urllib3_filter.filter(record))

        # Create our custom session-aware Logfire handler
        logfire_handler = SessionAwareLogfireHandler(
            level=_get_setting("log_level", "INFO").upper(),
            fallback=fallback_handler,
            logfire_instance=logfire,
        )

        # Get replay_llm_call logger and add Logfire handler (avoid duplicates)
        agent_logger = logging.getLogger("replay_llm_call")
        if not any(
            isinstance(h, SessionAwareLogfireHandler) for h in agent_logger.handlers
        ):
            agent_logger.addHandler(logfire_handler)

        # Log successful Logfire integration
        logger = logging.getLogger("replay_llm_call.logfire")
        logger.info("Session-aware Logfire logging handler configured successfully")

    except ImportError:
        logger = logging.getLogger("replay_llm_call.logfire")
        logger.warning("Logfire not available, using standard logging only")
    except Exception as e:
        logger = logging.getLogger("replay_llm_call.logfire")
        logger.error("Failed to configure Logfire handler: %s", str(e))


@lru_cache(maxsize=1)
def setup_logging() -> None:
    """
    Set up logging configuration for the entire application.
    This function should be called once during application startup.
    """

    config = get_logging_config()
    logging.config.dictConfig(config)

    # Log startup information
    logger = logging.getLogger("replay_llm_call.startup")
    logger.info(
        "Logging system initialized - Environment: %s, Level: %s, Logfire: %s",
        _get_setting("environment", "development"),
        _get_setting("log_level", "info"),
        _get_setting("logfire__enabled", False),
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name, typically __name__ of the calling module

    Returns:
        Logger: Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("This is an info message")
    """

    # Ensure logging is set up
    setup_logging()

    # Get logger with replay_llm_call prefix if not already present
    if not name.startswith("replay_llm_call"):
        name = f"replay_llm_call.{name}"

    return logging.getLogger(name)


# Convenience function for backward compatibility
def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Set up and configure a logger (backward compatibility).

    Args:
        name: Logger name (optional)

    Returns:
        Logger: Configured logger instance
    """

    if name is None:
        name = "replay_llm_call.default"

    return get_logger(name)
