"""CRUD operations for MongoDB collections."""

from datetime import datetime, timezone
from typing import Optional
from pymongo import UpdateOne
from finder.db.session import Database
from finder.db.models import PageDocument, LinkDocument, CrawlJobDocument


async def upsert_page(page: PageDocument) -> bool:
    """Insert or update a page document. Returns True if inserted, False if updated."""
    db = Database.get_db()
    result = await db.pages.update_one(
        {"url": page.url},
        {"$set": page.to_dict()},
        upsert=True
    )
    return result.upserted_id is not None


async def insert_links(links: list[LinkDocument]) -> int:
    """Bulk insert links, ignoring duplicates. Returns count of inserted."""
    if not links:
        return 0
    db = Database.get_db()
    operations = []
    for link in links:
        operations.append(
            UpdateOne(
                {"source_url": link.source_url, "target_url": link.target_url},
                {"$set": link.to_dict()},
                upsert=True
            )
        )
    result = await db.links.bulk_write(operations, ordered=False)
    return result.upserted_count


async def get_page_by_url(url: str) -> Optional[dict]:
    """Get a page by its URL."""
    db = Database.get_db()
    return await db.pages.find_one({"url": url})


async def url_exists(url: str) -> bool:
    """Check if a URL has already been crawled."""
    db = Database.get_db()
    return await db.pages.find_one({"url": url}, {"_id": 1}) is not None


async def content_hash_exists(content_hash: str) -> bool:
    """Check if content with this hash already exists (duplicate detection)."""
    db = Database.get_db()
    return await db.pages.find_one({"content_hash": content_hash}, {"_id": 1}) is not None


async def get_all_pages(projection: Optional[dict] = None) -> list[dict]:
    """Get all crawled pages with optional field projection."""
    db = Database.get_db()
    cursor = db.pages.find({"status": "crawled"}, projection)
    return await cursor.to_list(length=None)


async def get_all_links() -> list[dict]:
    """Get all link documents."""
    db = Database.get_db()
    cursor = db.links.find({})
    return await cursor.to_list(length=None)


async def update_pagerank_scores(scores: dict[str, float]) -> int:
    """Bulk update PageRank scores for pages. scores = {url: score}."""
    if not scores:
        return 0
    db = Database.get_db()
    operations = [
        UpdateOne({"url": url}, {"$set": {"pagerank_score": score}})
        for url, score in scores.items()
    ]
    result = await db.links.bulk_write(operations, ordered=False)
    # Also update in pages collection
    operations_pages = [
        UpdateOne({"url": url}, {"$set": {"pagerank_score": score}})
        for url, score in scores.items()
    ]
    result = await db.pages.bulk_write(operations_pages, ordered=False)
    return result.modified_count


async def create_crawl_job(job: CrawlJobDocument) -> str:
    """Create a new crawl job record. Returns the job ID."""
    db = Database.get_db()
    result = await db.crawl_jobs.insert_one(job.to_dict())
    return str(result.inserted_id)


async def update_crawl_job(job_id: str, **kwargs):
    """Update a crawl job record."""
    from bson import ObjectId
    db = Database.get_db()
    await db.crawl_jobs.update_one(
        {"_id": ObjectId(job_id)},
        {"$set": kwargs}
    )


async def get_crawl_stats() -> dict:
    """Get aggregate crawl statistics."""
    db = Database.get_db()
    total_pages = await db.pages.count_documents({})
    crawled_pages = await db.pages.count_documents({"status": "crawled"})
    failed_pages = await db.pages.count_documents({"status": "failed"})
    total_links = await db.links.count_documents({})
    unique_domains = len(await db.pages.distinct("domain"))

    return {
        "total_pages": total_pages,
        "crawled_pages": crawled_pages,
        "failed_pages": failed_pages,
        "total_links": total_links,
        "unique_domains": unique_domains,
    }
