"""
replay-llm-call - Main Entry Point

Supports both CLI and API modes for flexible deployment.
"""

import argparse
import asyncio
import os
import sys
from typing import Optional

from fastapi import FastAPI

# Only import essential configuration, avoid import-time side effects
settings: Optional["Settings"] = None
try:
    from src.core.config import Settings, settings
except ImportError:
    pass


async def run_cli_mode() -> None:
    """
    Run the application in CLI mode with a demo agent.
    """
    print("🤖 replay-llm-call - CLI Mode")
    print("=" * 50)

    if settings is None:
        print("⚠️  Configuration not fully loaded, but continuing with CLI mode...")

    # Initialize Logfire for CLI mode (without FastAPI app)
    try:
        from src.core.logfire_config import initialize_logfire

        results = initialize_logfire(app=None)
        if results["configured"]:
            instrumentation = results["instrumentation"]
            enabled_instruments = [
                name
                for name, enabled in instrumentation.items()
                if enabled and name != "fastapi"
            ]
            if enabled_instruments:
                print(f"🔍 Monitoring enabled for: {', '.join(enabled_instruments)}")
    except ImportError:
        pass  # Logfire not available
    except Exception:
        pass  # Ignore Logfire initialization errors in CLI mode

    print("Welcome to the replay-llm-call!")
    print("This is a demo CLI interface. You can extend this with your own agents.")
    print("\nAvailable commands:")
    print("  - Type 'help' for this message")
    print("  - Type 'exit' or 'quit' to exit")
    print("  - Type anything else for a demo response")
    print()

    while True:
        try:
            user_input = input("🤖 > ").strip()

            if user_input.lower() in ["exit", "quit"]:
                print("👋 Goodbye!")
                break
            elif user_input.lower() == "help":
                print("\nAvailable commands:")
                print("  - help: Show this help message")
                print("  - exit/quit: Exit the application")
                print("  - Any other text: Get a demo response")
                print()
            elif user_input:
                # Demo response - replace this with your actual agent logic
                print(
                    f"🤖 Demo Agent: You said '{user_input}'. This is where your agent logic would go!"
                )
                print("   💡 Tip: Implement your agent in replay_llm_call/agents/")
                print()
            else:
                print("Please enter a command or message.")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except EOFError:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def create_app() -> FastAPI:
    """
    Factory function to create FastAPI application.

    This function is called by uvicorn in factory mode to avoid
    import-time side effects when running in CLI mode.

    Returns:
        FastAPI: Configured application instance
    """
    # Lazy import API components to avoid side effects in CLI mode
    try:
        from src.api.factory import create_api
        from src.core.logger import setup_logging

        # Setup logging first
        setup_logging()

        # Create API with settings if available
        if settings:
            return create_api(
                title=settings.api__title,
                description=settings.api__description,
                version=settings.api__version,
                docs_url=settings.api__docs_url,
                redoc_url=settings.api__redoc_url,
                mount_prefix="",  # Mount at root level
            )
        else:
            # Fallback configuration
            return create_api(
                title="replay-llm-call",
                description="AI Agent Application Template",
                version="1.0.0",
                docs_url="/docs",
                redoc_url="/redoc",
                mount_prefix="",
            )

    except ImportError:
        # Fallback if API components are not available
        app = FastAPI(
            title="replay-llm-call",
            description="AI Agent Application Template (Minimal Mode)",
            version="1.0.0",
        )

        @app.get("/")
        async def root() -> dict[str, str]:
            return {
                "message": "replay-llm-call API",
                "status": "running",
                "note": "Running in minimal mode due to missing components",
            }

        return app


def main() -> None:
    """
    Main entry point with CLI argument parsing.
    """
    parser = argparse.ArgumentParser(
        description="replay-llm-call - AI Agent Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --mode cli          # Run in CLI mode (default)
  python main.py --mode api          # Run as FastAPI server
  python main.py --mode api --host 127.0.0.1 --port 3000  # Custom host/port
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["cli", "api"],
        default="cli",
        help="Run mode: 'cli' for command-line interface, 'api' for FastAPI server (default: cli)",
    )

    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host to bind the API server (default: 0.0.0.0)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8080")),
        help="Port to bind the API server (default: 8080)",
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development (API mode only)",
    )

    args = parser.parse_args()

    if args.mode == "cli":
        # Run in CLI mode
        try:
            asyncio.run(run_cli_mode())
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        except Exception as e:
            print(f"❌ Error running CLI mode: {e}")
            sys.exit(1)

    elif args.mode == "api":
        # Run in API mode
        if settings is None:
            print(
                "⚠️  Configuration not fully loaded, but starting API server with defaults..."
            )

        print("🚀 Starting replay-llm-call API Server...")
        print(f"📍 Server will run on {args.host}:{args.port}")

        if settings:
            print(f"🌍 Environment: {settings.environment}")
            print(f"🐛 Debug mode: {settings.debug}")
            print(
                f"📚 API docs: http://{args.host}:{args.port}{settings.api__docs_url}"
            )
            print(f"📖 ReDoc: http://{args.host}:{args.port}{settings.api__redoc_url}")
        else:
            print("🌍 Environment: development (fallback)")
            print("🐛 Debug mode: true (fallback)")
            print(f"📚 API docs: http://{args.host}:{args.port}/docs")
            print(f"📖 ReDoc: http://{args.host}:{args.port}/redoc")
        print()

        try:
            # Import uvicorn here to avoid import-time side effects in CLI mode
            import uvicorn

            uvicorn.run(
                "main:create_app",  # Use factory function to avoid import-time app creation
                factory=True,  # Enable factory mode
                host=args.host,
                port=args.port,
                reload=args.reload or (settings.debug if settings else True),
                log_level=str(settings.log_level).lower() if settings else "info",
            )
        except Exception as e:
            print(f"❌ Error starting API server: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
