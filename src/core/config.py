"""
Configuration

Application settings and environment configuration for replay-llm-call.
"""

from typing import List, Literal, Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

STATIC_ASSET_VERSION = "202509221245"


class Settings(BaseSettings):
    """
    Application configuration settings.

    Supports both environment variables and .env file loading.
    Environment variables take precedence over .env file values.
    """

    # Application settings
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(
        default="info", description="Log level (debug, info, warning, error)"
    )
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Application environment"
    )
    static__asset_version: str = Field(
        default=STATIC_ASSET_VERSION,
        description="Cache-busting version appended to static asset URLs",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Normalize and validate log level."""
        allowed_levels = {"debug", "info", "warning", "error"}
        normalized = v.lower().strip()
        if normalized not in allowed_levels:
            raise ValueError(
                f"log_level must be one of {sorted(allowed_levels)}, got '{v}'"
            )
        return normalized

    # API settings
    api__title: str = Field(default="replay-llm-call", description="API title")
    api__description: str = Field(
        default="AI Agent Application", description="API description"
    )
    api__version: str = Field(default="1.0.0", description="API version")
    api__docs_url: str = Field(default="/docs", description="API documentation URL")
    api__redoc_url: str = Field(default="/redoc", description="ReDoc documentation URL")

    # CORS settings
    cors__allow_origins: str = Field(
        default="*", description="Allowed origins for CORS (comma-separated)"
    )
    cors__allow_credentials: bool = Field(
        default=False, description="Allow credentials in CORS"
    )
    cors__allow_methods: str = Field(
        default="GET,POST,PUT,DELETE",
        description="Allowed HTTP methods (comma-separated)",
    )
    cors__allow_headers: str = Field(
        default="*", description="Allowed headers (comma-separated)"
    )

    # Database settings (optional)
    database__url: str = Field(
        default="postgresql://user:password@localhost:5432/agent_db",
        description="Database connection URL",
    )
    database__echo: bool = Field(default=False, description="Enable SQL query logging")
    database__pool_size: int = Field(
        default=10, ge=1, description="Connection pool size"
    )
    database__max_overflow: int = Field(
        default=20, ge=0, description="Maximum overflow connections"
    )
    database__pool_timeout: int = Field(
        default=30, ge=0, description="Pool timeout in seconds"
    )
    database__pool_recycle: int = Field(
        default=3600, ge=0, description="Pool recycle time in seconds"
    )
    database__pool_pre_ping: bool = Field(
        default=True, description="Enable pool pre-ping"
    )

    # Redis settings (optional)
    redis__host: str = Field(default="localhost", description="Redis host")
    redis__port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis__db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    redis__password: Optional[str] = Field(default=None, description="Redis password")
    redis__ssl: bool = Field(
        default=False, description="Enable SSL/TLS for Redis connection"
    )
    redis__connect_timeout: float = Field(
        default=3.0, gt=0, description="Redis connection timeout in seconds"
    )
    redis__socket_timeout: float = Field(
        default=3.0, gt=0, description="Redis socket timeout in seconds"
    )

    # Lock configuration
    redis_lock__retry_sleep_interval: float = Field(
        default=0.1, description="Lock retry sleep interval in seconds"
    )

    # Health check configuration
    health__check_database: bool = Field(
        default=False, description="Enable database health check"
    )
    health__check_redis: bool = Field(
        default=False, description="Enable Redis health check"
    )

    # AI API Keys (secured with SecretStr)
    ai__openai_api_key: Optional[SecretStr] = Field(
        default=None, description="OpenAI API key"
    )
    ai__anthropic_api_key: Optional[SecretStr] = Field(
        default=None, description="Anthropic API key"
    )
    ai__google_api_key: Optional[SecretStr] = Field(
        default=None, description="Google API key"
    )
    ai__openrouter_api_key: Optional[SecretStr] = Field(
        default=None, description="OpenRouter API key"
    )

    # Model configurations
    ai__default_model__provider: str = Field(
        default="openrouter", description="Default model provider"
    )
    ai__default_model__name: str = Field(
        default="openai/gpt-4o-mini", description="Default model name"
    )

    # Business-oriented model configurations (examples)
    ai__demo_agent__provider: str = Field(
        default="openrouter", description="Provider for demo agent"
    )
    ai__demo_agent__model_name: str = Field(
        default="openai/gpt-4o-mini", description="Model name for demo agent"
    )

    # Add more business-specific agents as needed:
    # ai__chat_agent__provider: str = Field(default="anthropic", description="Provider for chat agent")
    # ai__chat_agent__model_name: str = Field(default="claude-3-5-sonnet-20241022", description="Model name for chat agent")
    # ai__analysis_agent__provider: str = Field(default="google", description="Provider for analysis agent")
    # ai__analysis_agent__model_name: str = Field(default="gemini-1.5-pro", description="Model name for analysis agent")

    # Fallback model configuration (used when primary models fail)
    ai__fallback__provider: str = Field(
        default="openai", description="Provider for fallback model"
    )
    ai__fallback__model_name: str = Field(
        default="gpt-4o-mini", description="Model name for fallback model"
    )

    # Logfire monitoring settings
    logfire__enabled: bool = Field(
        default=False, description="Enable Logfire monitoring"
    )
    logfire__service_name: str = Field(
        default="replay_llm_call", description="Logfire service name"
    )
    logfire__environment: str = Field(
        default="development", description="Logfire environment"
    )
    logfire__token: Optional[SecretStr] = Field(
        default=None, description="Logfire token"
    )
    logfire__disable_scrubbing: Optional[bool] = Field(
        default=False, description="Disable Logfire scrubbing"
    )

    # Optional Logfire instrumentation toggles
    logfire__instrument__pydantic_ai: bool = Field(
        default=True, description="Enable Logfire pydantic-ai instrumentation"
    )
    logfire__instrument__redis: bool = Field(
        default=True, description="Enable Logfire Redis instrumentation"
    )
    logfire__instrument__httpx: bool = Field(
        default=True, description="Enable Logfire HTTPX instrumentation"
    )
    logfire__instrument__fastapi: bool = Field(
        default=True, description="Enable Logfire FastAPI instrumentation"
    )
    logfire__httpx_capture_all: bool = Field(
        default=False, description="Capture all HTTPX requests (can be verbose)"
    )

    # Logging file settings (optional)
    log__dir: str = Field(
        default="logs", description="Directory where log files are stored"
    )
    log__file_path: Optional[str] = Field(
        default=None, description="Custom log file path; overrides log__dir if set"
    )
    log__file_level: str = Field(default="INFO", description="File handler log level")
    log__file_max_bytes: int = Field(
        default=10 * 1024 * 1024,
        gt=0,
        description="Max size of a log file before rotation",
    )
    log__file_backup_count: int = Field(
        default=3, ge=0, description="Number of backup log files to keep"
    )

    # File upload settings
    upload_max_size: int = Field(
        default=10 * 1024 * 1024,
        gt=0,
        description="Maximum file upload size in bytes (10MB)",
    )
    upload_allowed_extensions: str = Field(
        default=".txt,.md,.json",
        description="Allowed file extensions (comma-separated)",
    )

    # Properties for list conversion
    @property
    def cors_allow_origins_list(self) -> List[str]:
        """Convert comma-separated origins to list."""
        return [origin.strip() for origin in str(self.cors__allow_origins).split(",")]

    @property
    def cors_allow_methods_list(self) -> List[str]:
        """Convert comma-separated methods to list."""
        return [method.strip() for method in str(self.cors__allow_methods).split(",")]

    @property
    def cors_allow_headers_list(self) -> List[str]:
        """Convert comma-separated headers to list."""
        return [header.strip() for header in str(self.cors__allow_headers).split(",")]

    @property
    def upload_allowed_extensions_list(self) -> List[str]:
        """Convert comma-separated extensions to list."""
        return [ext.strip() for ext in str(self.upload_allowed_extensions).split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_nested_delimiter="__",
    )


def create_settings() -> Settings:
    """
    Create and validate settings instance.

    Returns:
        Settings: Configured settings instance

    Raises:
        RuntimeError: If configuration validation fails
    """
    try:
        settings_instance = Settings()

        # Environment validation is now handled by Literal type annotation

        # Count configured API keys
        api_keys_count = len(
            [
                key
                for key in [
                    settings_instance.ai__openai_api_key,
                    settings_instance.ai__anthropic_api_key,
                    settings_instance.ai__google_api_key,
                    settings_instance.ai__openrouter_api_key,
                ]
                if key
            ]
        )

        print("🔧 Configuration loaded successfully")
        print(f"   Environment: {settings_instance.environment}")
        print(f"   Debug mode: {settings_instance.debug}")
        print(f"   Log level: {settings_instance.log_level}")
        print(f"   API keys configured: {api_keys_count}/4")

        if api_keys_count == 0:
            print("⚠️  Warning: No AI API keys configured. Some features may not work.")
            print(
                "   Set AI__OPENAI_API_KEY, AI__ANTHROPIC_API_KEY, etc. in your .env file"
            )

        return settings_instance

    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        print("Please ensure all required environment variables are set")
        raise RuntimeError(f"Configuration loading failed: {e}") from e


# Global configuration instance
settings = create_settings()
