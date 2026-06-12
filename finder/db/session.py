"""MongoDB connection manager using motor (async driver)."""

import motor.motor_asyncio
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
from finder.config import settings


class Database:
    """Async MongoDB connection manager."""

    _client: motor.motor_asyncio.AsyncIOMotorClient = None
    _db: motor.motor_asyncio.AsyncIOMotorDatabase = None

    @classmethod
    async def connect(cls):
        """Initialize the MongoDB connection and create indexes."""
        cls._client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongodb_url)
        cls._db = cls._client[settings.mongodb_db_name]

        # Create indexes for the pages collection
        pages = cls._db.pages
        await pages.create_indexes([
            IndexModel([("url", ASCENDING)], unique=True),
            IndexModel([("domain", ASCENDING)]),
            IndexModel([("content_hash", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("crawled_at", DESCENDING)]),
            IndexModel([("pagerank_score", DESCENDING)]),
            IndexModel([("title", TEXT), ("extracted_text", TEXT)], name="pages_text_index", weights={"title": 3, "extracted_text": 1}),
        ])

        # Create indexes for the links collection
        links = cls._db.links
        await links.create_indexes([
            IndexModel([("source_url", ASCENDING)]),
            IndexModel([("target_url", ASCENDING)]),
            IndexModel([("source_url", ASCENDING), ("target_url", ASCENDING)], unique=True),
        ])

        # Create indexes for crawl_jobs collection
        jobs = cls._db.crawl_jobs
        await jobs.create_indexes([
            IndexModel([("started_at", DESCENDING)]),
            IndexModel([("status", ASCENDING)]),
        ])

        return cls._db

    @classmethod
    def get_db(cls) -> motor.motor_asyncio.AsyncIOMotorDatabase:
        """Get the database instance."""
        if cls._db is None:
            raise RuntimeError("Database not connected. Call Database.connect() first.")
        return cls._db

    @classmethod
    async def close(cls):
        """Close the MongoDB connection."""
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None
