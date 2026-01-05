"""Tests for LLM parser service."""

from src.services.llm_parser_service import parse_llm_raw_data


def test_parse_pydantic_ai_with_system_instructions():
    """Test parsing pydantic-ai format with gen_ai.system_instructions field."""
    raw_data = {
        "attributes": {
            "gen_ai.input.messages": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "type": "text",
                            "content": "This is the user message content.",
                        }
                    ],
                }
            ],
            "gen_ai.request.model": "google/gemini-3-flash-preview",
            "gen_ai.request.temperature": 0.2,
            "gen_ai.request.max_tokens": 1000,
            "gen_ai.system_instructions": [
                {
                    "type": "text",
                    "content": "You are a job search consultant helping users.",
                }
            ],
        }
    }

    result = parse_llm_raw_data(raw_data)

    assert result.system_prompt == "You are a job search consultant helping users."
    assert result.last_user_message == "This is the user message content."
    assert result.model_name == "google/gemini-3-flash-preview"
    assert result.model_settings == {"temperature": 0.2, "max_tokens": 1000}
    assert result.middle_messages == []


def test_parse_pydantic_ai_with_system_instructions_parts_format():
    """Test parsing pydantic-ai format with system_instructions in parts format."""
    raw_data = {
        "attributes": {
            "gen_ai.input.messages": [
                {
                    "role": "user",
                    "parts": [{"content": "User question here."}],
                }
            ],
            "gen_ai.request.model": "openai/gpt-4",
            "gen_ai.system_instructions": [
                {
                    "parts": [
                        {"content": "Part 1 of system prompt."},
                        {"content": "Part 2 of system prompt."},
                    ]
                }
            ],
        }
    }

    result = parse_llm_raw_data(raw_data)

    assert result.system_prompt == "Part 1 of system prompt.\nPart 2 of system prompt."
    assert result.last_user_message == "User question here."


def test_parse_pydantic_ai_without_system_instructions():
    """Test parsing pydantic-ai format without gen_ai.system_instructions."""
    raw_data = {
        "attributes": {
            "gen_ai.input.messages": [
                {
                    "role": "system",
                    "parts": [{"content": "System prompt in messages."}],
                },
                {
                    "role": "user",
                    "parts": [{"content": "User message."}],
                },
            ],
            "gen_ai.request.model": "openai/gpt-4",
        }
    }

    result = parse_llm_raw_data(raw_data)

    assert result.system_prompt == "System prompt in messages."
    assert result.last_user_message == "User message."


def test_parse_pydantic_ai_both_system_sources():
    """Test that gen_ai.system_instructions takes precedence over system role in messages."""
    raw_data = {
        "attributes": {
            "gen_ai.input.messages": [
                {
                    "role": "system",
                    "parts": [{"content": "System in messages (ignored)."}],
                },
                {
                    "role": "user",
                    "parts": [{"content": "User message."}],
                },
            ],
            "gen_ai.request.model": "openai/gpt-4",
            "gen_ai.system_instructions": [
                {"content": "System from instructions (used)."}
            ],
        }
    }

    result = parse_llm_raw_data(raw_data)

    # gen_ai.system_instructions should be added first as system message
    # The system message from input.messages becomes part of the conversation
    assert result.system_prompt == "System from instructions (used)."
    assert result.last_user_message == "User message."


def test_parse_pydantic_ai_real_world_format():
    """Test with actual pydantic-ai OpenTelemetry span format from production."""
    raw_data = {
        "start_timestamp": "2025-12-31T05:08:16.662811Z",
        "trace_id": "019b72ce8894e4723bf9c60a39c42214",
        "span_id": "927cd91911d8270d",
        "span_name": "chat google/gemini-3-flash-preview",
        "otel_scope_name": "pydantic-ai",
        "attributes": {
            "gen_ai.input.messages": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "type": "text",
                            "content": "## Search Strategy\nI will search for entry-level quantitative roles.",
                        }
                    ],
                }
            ],
            "gen_ai.operation.name": "chat",
            "gen_ai.output.messages": [
                {
                    "role": "assistant",
                    "parts": [{"type": "text", "content": '```json\n{"result": "ok"}\n```'}],
                    "finish_reason": "stop",
                }
            ],
            "gen_ai.request.max_tokens": 1000,
            "gen_ai.request.model": "google/gemini-3-flash-preview",
            "gen_ai.request.temperature": 0.2,
            "gen_ai.system_instructions": [
                {
                    "type": "text",
                    "content": "You are a job search consultant helping to convert a user's job search strategy into structured search parameters.",
                }
            ],
            "gen_ai.usage.input_tokens": 2973,
            "gen_ai.usage.output_tokens": 212,
        },
    }

    result = parse_llm_raw_data(raw_data)

    assert (
        result.system_prompt
        == "You are a job search consultant helping to convert a user's job search strategy into structured search parameters."
    )
    assert "## Search Strategy" in result.last_user_message
    assert result.model_name == "google/gemini-3-flash-preview"
    assert result.model_settings == {"temperature": 0.2, "max_tokens": 1000}
