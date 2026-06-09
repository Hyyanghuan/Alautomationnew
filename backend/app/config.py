"""统一配置中心 - 从项目根目录 .env 加载所有配置"""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录 .env（本地开发: repo根目录；Docker: /app/.env）
_ROOT_CANDIDATES = [
    Path(__file__).resolve().parent.parent.parent,
    Path(__file__).resolve().parent.parent,
    Path("/app"),
]
ENV_FILE = next((p / ".env" for p in _ROOT_CANDIDATES if (p / ".env").exists()), _ROOT_CANDIDATES[0] / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    app_name: str = Field("AI自动化测试平台", alias="APP_NAME")
    app_version: str = Field("3.0.0", alias="APP_VERSION")
    app_env: str = Field("development", alias="APP_ENV")
    app_debug: bool = Field(True, alias="APP_DEBUG")
    app_secret_key: str = Field(..., alias="APP_SECRET_KEY")
    app_host: str = Field("0.0.0.0", alias="APP_HOST")
    app_port: int = Field(8000, alias="APP_PORT")
    app_cors_origins: str = Field(
        "http://localhost:5173", alias="APP_CORS_ORIGINS"
    )
    app_cors_allow_all: bool = Field(False, alias="APP_CORS_ALLOW_ALL")

    # 数据库
    database_url: str = Field(..., alias="DATABASE_URL")

    # Redis
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    # MinIO
    minio_endpoint: str = Field("localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field("minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field("minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field("ai-test-platform", alias="MINIO_BUCKET")
    minio_secure: bool = Field(False, alias="MINIO_SECURE")

    # JWT
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        1440, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # 超级管理员
    super_admin_username: str = Field("admin", alias="SUPER_ADMIN_USERNAME")
    super_admin_password: str = Field("admin123", alias="SUPER_ADMIN_PASSWORD")
    super_admin_email: str = Field(
        "admin@example.com", alias="SUPER_ADMIN_EMAIL"
    )

    # AI 默认
    ai_default_provider: str = Field("openai", alias="AI_DEFAULT_PROVIDER")
    ai_default_model: str = Field("gpt-4o", alias="AI_DEFAULT_MODEL")
    ai_default_temperature: float = Field(0.7, alias="AI_DEFAULT_TEMPERATURE")
    ai_default_top_p: float = Field(0.9, alias="AI_DEFAULT_TOP_P")
    ai_default_max_tokens: int = Field(4096, alias="AI_DEFAULT_MAX_TOKENS")
    ai_request_timeout: int = Field(120, alias="AI_REQUEST_TIMEOUT")
    ai_max_retries: int = Field(3, alias="AI_MAX_RETRIES")

    openai_api_key: str = Field("", alias="OPENAI_API_KEY")
    openai_api_base: str = Field(
        "https://api.openai.com/v1", alias="OPENAI_API_BASE"
    )
    qwen_api_key: str = Field("", alias="QWEN_API_KEY")
    qwen_api_base: str = Field(
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        alias="QWEN_API_BASE",
    )
    deepseek_api_key: str = Field("", alias="DEEPSEEK_API_KEY")
    deepseek_api_base: str = Field(
        "https://api.deepseek.com/v1", alias="DEEPSEEK_API_BASE"
    )

    # 知识库
    kb_chunk_size: int = Field(512, alias="KB_CHUNK_SIZE")
    kb_chunk_overlap: int = Field(50, alias="KB_CHUNK_OVERLAP")
    kb_embedding_model: str = Field(
        "text-embedding-ada-002", alias="KB_EMBEDDING_MODEL"
    )
    kb_top_k: int = Field(5, alias="KB_TOP_K")

    # 执行引擎
    executor_max_retry: int = Field(3, alias="EXECUTOR_MAX_RETRY")
    executor_timeout_seconds: int = Field(300, alias="EXECUTOR_TIMEOUT_SECONDS")
    executor_parallel_workers: int = Field(4, alias="EXECUTOR_PARALLEL_WORKERS")
    playwright_browsers_path: str = Field(
        "/app/data/browsers", alias="PLAYWRIGHT_BROWSERS_PATH"
    )
    playwright_screenshots_path: str = Field(
        "/app/data/screenshots", alias="PLAYWRIGHT_SCREENSHOTS_PATH"
    )

    # Celery
    celery_broker_url: str = Field(
        "redis://localhost:6379/1", alias="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        "redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND"
    )

    # Webhook
    webhook_secret: str = Field("", alias="WEBHOOK_SECRET")

    # Telegram 测试报告推送
    telegram_bot_token: str = Field("", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field("", alias="TELEGRAM_CHAT_ID")
    telegram_enabled: bool = Field(False, alias="TELEGRAM_ENABLED")
    telegram_auto_send: bool = Field(False, alias="TELEGRAM_AUTO_SEND")

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.app_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
