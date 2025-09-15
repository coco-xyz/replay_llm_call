"""
Demo API Endpoints

Simple demonstration endpoints for the replay-llm-call.
"""

from fastapi import APIRouter

from src.agents import handle_demo_agent
from src.api.schemas.error import ErrorResponse
from src.api.v1.schemas.requests import DemoChatRequest
from src.api.v1.schemas.responses import DemoChatResponse
from src.core.error_codes import AgentErrorCode
from src.core.exceptions import AgentException

router = APIRouter()


@router.post(
    "/chat",
    response_model=DemoChatResponse,
    summary="Chat with Demo Agent",
    description="Send a message to the demo agent and get a response",
    tags=["demo"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Agent unavailable"},
    },
)
async def chat_with_agent(request: DemoChatRequest) -> DemoChatResponse:
    """
    Chat with the demo agent.

    Args:
        request: ChatRequest containing the message and optional context

    Returns:
        ChatResponse: Agent's response

    Raises:
        HTTPException: If agent is not available or processing fails
    """
    try:
        # Handle the chat request
        response = await handle_demo_agent(request.message)

        return DemoChatResponse(
            response=response, session_id=request.session_id, status="success"
        )

    except Exception as e:
        raise AgentException.wrap(
            e,
            message="Error processing chat request",
            error_code=AgentErrorCode.RUN_FAILED,
        )
