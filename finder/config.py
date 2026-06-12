"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Global settings for the Finder search engine."""

    # MongoDB
    mongodb_url: str = Field(default="mongodb://localhost:27017")
    mongodb_db_name: str = Field(default="finder")

    # Elasticsearch
    elasticsearch_url: str = Field(default="http://localhost:9200")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Crawler
    crawler_concurrency: int = Field(default=10)
    crawler_rate_limit: float = Field(default=2.0, description="Max requests per second per domain")
    crawler_max_depth: int = Field(default=3)
    crawler_user_agent: str = Field(default="FinderBot/1.0 (+https://github.com/finder-search)")
    raw_html_dir: str = Field(default="./data/raw_html")

    # Ranker
    ranker_alpha: float = Field(default=0.7, description="Weight for BM25 score")
    ranker_beta: float = Field(default=0.3, description="Weight for PageRank score")

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Singleton
settings = Settings()
