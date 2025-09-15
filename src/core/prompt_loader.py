"""
Prompt Loader Utility

This module provides a utility for loading prompt text from files
in the `prompts` directory.

The loader uses LRU caching (maxsize=128) to improve performance by avoiding
repeated file I/O operations. Use clear_prompt_cache() to manually clear the
cache when prompt files are updated during runtime.
"""

from functools import lru_cache
from pathlib import Path

from src.core.error_codes import InternalServiceErrorCode
from src.core.exceptions import InternalServiceException

# Get the absolute path to the 'prompts' directory
# This makes the loader independent of where the script is run
PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache(maxsize=128)
def load_prompt(prompt_name: str) -> str:
    """
    Load a prompt from the 'prompts' directory.

    Args:
        prompt_name (str): The filename of the prompt (e.g., 'resume_parser.txt')

    Returns:
        str: The content of the prompt file.

    Raises:
        InternalServiceException: If the prompt file is not found or cannot be read.
    """
    # Resolve paths and validate against directory traversal
    base_dir = PROMPT_DIR.resolve()
    target_path = (base_dir / prompt_name).resolve()

    # Security check: ensure target path is within the prompts directory
    if not str(target_path).startswith(str(base_dir)):
        raise InternalServiceException(
            "Invalid prompt path outside prompts directory",
            InternalServiceErrorCode.OPERATION_FAILED,
            {"prompt_name": prompt_name},
        )

    try:
        return target_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise InternalServiceException(
            f"Prompt file not found at: {target_path}",
            InternalServiceErrorCode.OPERATION_FAILED,
            {"prompt_name": prompt_name, "file_path": str(target_path)},
        ) from exc
    except Exception as e:
        raise InternalServiceException.wrap(
            e,
            f"Failed to load prompt file {prompt_name}",
            InternalServiceErrorCode.OPERATION_FAILED,
            prompt_name=prompt_name,
            file_path=str(target_path),
        )


def clear_prompt_cache() -> None:
    """
    Clear the prompt loading cache.

    This function should be called when prompt files are updated during runtime
    to ensure the latest content is loaded on subsequent calls to load_prompt().
    """
    load_prompt.cache_clear()
