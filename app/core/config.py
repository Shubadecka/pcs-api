"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
JWT_EXPIRY_HOURS = os.getenv("JWT_EXPIRY_HOURS")

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database settings
    database_host: str = DATABASE_HOST
    database_port: int = DATABASE_PORT
    database_name: str = DATABASE_NAME
    database_user: str = DATABASE_USER
    database_password: str = DATABASE_PASSWORD
    
    @property
    def database_url(self) -> str:
        """Construct the database URL from components."""
        return f"postgresql://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"
    
    # JWT settings
    jwt_secret_key: str = JWT_SECRET_KEY
    jwt_algorithm: str = JWT_ALGORITHM
    jwt_expiry_hours: int = JWT_EXPIRY_HOURS
    
    # Server settings
    api_host: str = "localhost"
    api_port: int = 1442
    
    # File upload settings
    upload_dir: str = "./uploads"
    max_upload_size: int = 50 * 1024 * 1024  # 50MB

    # Ollama settings
    ollama_host: str = "host.docker.internal"
    ollama_port: int = 11434
    ocr_model: str = ""
    response_model: str = ""
    embedding_model: str = ""
    embedding_dim: int = 1024
    
    # Agentic cleanup settings
    agent_max_iterations: int = 10
    agent_context_size: int = 8192
    agent_batch_size: int = 64

    # CORS settings
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3001"]

    # Email allowlist settings
    # Set RESTRICT_EMAIL_DOMAINS=true to enable, then list allowed domains in ALLOWED_EMAIL_DOMAINS
    restrict_email_domains: bool = False
    # Stored as a raw comma-separated string to avoid pydantic-settings JSON-decoding it
    allowed_email_domains: str = ""

    @property
    def allowed_email_domains_list(self) -> list[str]:
        return [d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
