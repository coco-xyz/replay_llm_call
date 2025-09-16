"""
Pages API

Serves HTML pages for the LLM Replay System frontend.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """
    Home page - redirects to test cases.
    """
    return templates.TemplateResponse("test_cases.html", {"request": request})


@router.get("/test-cases", response_class=HTMLResponse)
async def test_cases_page(request: Request):
    """
    Test cases management page.
    """
    return templates.TemplateResponse("test_cases.html", {"request": request})


@router.get("/test-execution", response_class=HTMLResponse)
async def test_execution_page(request: Request):
    """
    Test execution page.
    """
    return templates.TemplateResponse("test_execution.html", {"request": request})


@router.get("/test-logs", response_class=HTMLResponse)
async def test_logs_page(request: Request):
    """
    Test logs viewing page.
    """
    return templates.TemplateResponse("test_logs.html", {"request": request})


__all__ = ["router"]
