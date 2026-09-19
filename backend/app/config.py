from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Shubankar's Mini AI RAG Assistant"
    app_env: str = "development"
    log_level: str = "INFO"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    # LLM Providers
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    deepseek_api_key: str = ""
    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4o-mini"

    # Local LLM
    ollama_base_url: str = "http://localhost:11434"
    llama_cpp_base_url: str = "http://localhost:8080"

    # Embeddings
    embedding_provider: str = "local"
    embedding_model: str = "nomic-embed-text"
    embedding_dimension: int = 768

    # Chroma
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection: str = "knowledge_base"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_session_ttl: int = 86400
    redis_cache_ttl: int = 1800

    # Retrieval
    retrieval_top_k: int = 5
    retrieval_vector_weight: float = 0.7
    retrieval_bm25_weight: float = 0.3
    retrieval_rrf_k: int = 60

    # Caching
    l1_cache_max_size: int = 1000
    l1_cache_ttl: int = 300
    l2_cache_ttl: int = 1800
    semantic_cache_threshold: float = 0.85
    semantic_cache_enabled: bool = True

    # Context
    hot_window_size: int = 10
    summarization_threshold: int = 6
    max_context_tokens: int = 8000

    # Storage
    upload_dir: str = "./data/uploads"
    parsed_dir: str = "./data/parsed"
    max_upload_size_mb: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()