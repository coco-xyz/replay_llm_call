"""
Pages API

Serves HTML pages for the LLM Replay System frontend.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """
    Home page - redirects to test cases.
    """
    return templates.TemplateResponse(
        "test_cases.html",
        {
            "request": request,
            "static_asset_version": settings.static__asset_version,
            "active_page": "test-cases",
        },
    )


@router.get("/test-cases", response_class=HTMLResponse)
async def test_cases_page(request: Request):
    """
    Test cases management page.
    """
    return templates.TemplateResponse(
        "test_cases.html",
        {
            "request": request,
            "static_asset_version": settings.static__asset_version,
            "active_page": "test-cases",
        },
    )


@router.get("/test-execution", response_class=HTMLResponse)
async def test_execution_page(request: Request):
    """
    Test execution page.
    """
    return templates.TemplateResponse(
        "test_execution.html",
        {
            "request": request,
            "static_asset_version": settings.static__asset_version,
            "active_page": "test-execution",
        },
    )


@router.get("/test-logs", response_class=HTMLResponse)
async def test_logs_page(request: Request):
    """
    Test logs viewing page.
    """
    return templates.TemplateResponse(
        "test_logs.html",
        {
            "request": request,
            "static_asset_version": settings.static__asset_version,
            "active_page": "test-logs",
        },
    )


@router.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request):
    """Agent management page."""

    return templates.TemplateResponse(
        "agents.html",
        {
            "request": request,
            "static_asset_version": settings.static__asset_version,
            "active_page": "agents",
        },
    )


@router.get("/agents/{agent_id}", response_class=HTMLResponse)
async def agent_detail_page(request: Request, agent_id: str):
    """Agent detail page."""

    return templates.TemplateResponse(
        "agent_detail.html",
        {
            "request": request,
            "agent_id": agent_id,
            "static_asset_version": settings.static__asset_version,
            "active_page": "agents",
        },
    )


@router.get("/regression-tests", response_class=HTMLResponse)
async def regression_tests_page(request: Request):
    """Regression tests listing page."""

    return templates.TemplateResponse(
        "regression_tests.html",
        {
            "request": request,
            "static_asset_version": settings.static__asset_version,
            "active_page": "regression-tests",
        },
    )


@router.get("/regression-tests/{regression_test_id}", response_class=HTMLResponse)
async def regression_test_detail_page(request: Request, regression_test_id: str):
    """Regression test detail page."""

    return templates.TemplateResponse(
        "regression_test_detail.html",
        {
            "request": request,
            "regression_test_id": regression_test_id,
            "static_asset_version": settings.static__asset_version,
            "active_page": "regression-tests",
        },
    )


@router.get("/test-cases/{case_id}", response_class=HTMLResponse)
async def test_case_detail_page(request: Request, case_id: str):
    """
    Test case detail page.
    """
    return templates.TemplateResponse(
        "test_case_detail.html",
        {
            "request": request,
            "case_id": case_id,
            "static_asset_version": settings.static__asset_version,
            "active_page": "test-cases",
        },
    )


@router.get("/test-logs/{log_id}", response_class=HTMLResponse)
async def test_log_detail_page(request: Request, log_id: str):
    """
    Test log detail page.
    """
    return templates.TemplateResponse(
        "test_log_detail.html",
        {
            "request": request,
            "log_id": log_id,
            "static_asset_version": settings.static__asset_version,
            "active_page": "test-logs",
        },
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Application settings page."""

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "static_asset_version": settings.static__asset_version,
            "active_page": "settings",
        },
    )


__all__ = ["router"]
