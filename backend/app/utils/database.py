"""
Database Utilities
==================
MongoDB connection and database access.
"""

from motor.motor_asyncio import AsyncIOMotorClient
import os

# Global database connection
_client = None
_db = None


def init_db():
    """Initialize database connection"""
    global _client, _db
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    
    if not mongo_url or not db_name:
        raise ValueError("MONGO_URL and DB_NAME must be set in environment")
    
    _client = AsyncIOMotorClient(mongo_url)
    _db = _client[db_name]
    return _db


def get_db():
    """Get database instance"""
    global _db
    if _db is None:
        init_db()
    return _db


def get_client():
    """Get MongoDB client"""
    global _client
    if _client is None:
        init_db()
    return _client
