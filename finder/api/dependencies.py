"""Dependency injection for FastAPI — ES, Redis, and DB clients."""

from functools import lru_cache
from typing import Optional

import redis
from elasticsearch import Elasticsearch

from finder.config import settings
from finder.ranker.scorer import Scorer


# Singleton instances
_es_client: Optional[Elasticsearch] = None
_redis_client: Optional[redis.Redis] = None
_scorer: Optional[Scorer] = None


def get_es_client() -> Elasticsearch:
    """Get or create the Elasticsearch client."""
    global _es_client
    if _es_client is None:
        _es_client = Elasticsearch(settings.elasticsearch_url)
    return _es_client


def get_redis_client() -> redis.Redis:
    """Get or create the Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def get_scorer() -> Scorer:
    """Get or create the Scorer instance."""
    global _scorer
    if _scorer is None:
        _scorer = Scorer(es_client=get_es_client())
    return _scorer


def close_clients():
    """Close all client connections."""
    global _es_client, _redis_client, _scorer
    if _es_client:
        _es_client.close()
        _es_client = None
    if _redis_client:
        _redis_client.close()
        _redis_client = None
    _scorer = None
