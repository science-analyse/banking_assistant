import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import asyncpg
from asyncpg import Pool
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Database connection pool
_pool: Optional[Pool] = None

class Database:
    """Database manager for the Kapital Bank AI Assistant"""
    
    def __init__(self):
        self.pool: Optional[Pool] = None
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./kapital_assistant.db")
        self.is_sqlite = self.database_url.startswith("sqlite")
        
    async def initialize(self):
        """Initialize database connection"""
        try:
            if self.is_sqlite:
                # For SQLite, we'll use a simple file-based approach
                import aiosqlite
                self.sqlite_path = self.database_url.replace("sqlite:///", "")
                logger.info(f"Using SQLite database: {self.sqlite_path}")
                await self._create_sqlite_tables()
            else:
                # For PostgreSQL
                self.pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=2,
                    max_size=10,
                    server_settings={
                        'jit': 'off'
                    }
                )
                logger.info("PostgreSQL database pool created")
                await self._create_postgres_tables()
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
    
    async def _create_sqlite_tables(self):
        """Create SQLite tables"""
        import aiosqlite
        
        async with aiosqlite.connect(self.sqlite_path) as db:
            # Cache table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User interactions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    interaction_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_latitude REAL,
                    user_longitude REAL,
                    language TEXT DEFAULT 'en'
                )
            """)
            
            # Locations cache table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS locations_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_type TEXT NOT NULL,
                    location_data TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Currency rates cache table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS currency_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    rates_data TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            await db.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_interactions_session ON user_interactions(session_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON user_interactions(timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_locations_service ON locations_cache(service_type)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_currency_source ON currency_cache(source)")
            
            await db.commit()
            logger.info("SQLite tables created successfully")
    
    async def _create_postgres_tables(self):
        """Create PostgreSQL tables"""
        async with self.pool.acquire() as conn:
            # Cache table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key VARCHAR(255) PRIMARY KEY,
                    data JSONB NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User interactions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_interactions (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    interaction_type VARCHAR(100) NOT NULL,
                    data JSONB NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_latitude DECIMAL(10, 8),
                    user_longitude DECIMAL(11, 8),
                    language VARCHAR(10) DEFAULT 'en'
                )
            """)
            
            # Locations cache table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS locations_cache (
                    id SERIAL PRIMARY KEY,
                    service_type VARCHAR(50) NOT NULL,
                    location_data JSONB NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Currency rates cache table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS currency_cache (
                    id SERIAL PRIMARY KEY,
                    source VARCHAR(50) NOT NULL,
                    rates_data JSONB NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_interactions_session ON user_interactions(session_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON user_interactions(timestamp)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_locations_service ON locations_cache(service_type)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_currency_source ON currency_cache(source)")
            
            logger.info("PostgreSQL tables created successfully")
    
    # Cache operations
    async def get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data"""
        try:
            if self.is_sqlite:
                return await self._get_cache_sqlite(key)
            else:
                return await self._get_cache_postgres(key)
        except Exception as e:
            logger.error(f"Error getting cache for key {key}: {e}")
            return None
    
    async def set_cache(self, key: str, data: Dict[str, Any], ttl_seconds: int = 3600):
        """Set cached data"""
        try:
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
            
            if self.is_sqlite:
                await self._set_cache_sqlite(key, data, expires_at)
            else:
                await self._set_cache_postgres(key, data, expires_at)
                
        except Exception as e:
            logger.error(f"Error setting cache for key {key}: {e}")
    
    async def _get_cache_sqlite(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cache from SQLite"""
        import aiosqlite
        
        async with aiosqlite.connect(self.sqlite_path) as db:
            async with db.execute(
                "SELECT data, expires_at FROM cache WHERE key = ? AND expires_at > CURRENT_TIMESTAMP",
                (key,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return None
    
    async def _set_cache_sqlite(self, key: str, data: Dict[str, Any], expires_at: datetime):
        """Set cache in SQLite"""
        import aiosqlite
        
        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO cache (key, data, expires_at) VALUES (?, ?, ?)",
                (key, json.dumps(data), expires_at.isoformat())
            )
            await db.commit()
    
    async def _get_cache_postgres(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cache from PostgreSQL"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT data FROM cache WHERE key = $1 AND expires_at > CURRENT_TIMESTAMP",
                key
            )
            return dict(result["data"]) if result else None
    
    async def _set_cache_postgres(self, key: str, data: Dict[str, Any], expires_at: datetime):
        """Set cache in PostgreSQL"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO cache (key, data, expires_at) VALUES ($1, $2, $3) "
                "ON CONFLICT (key) DO UPDATE SET data = $2, expires_at = $3",
                key, json.dumps(data), expires_at
            )
    
    # Location cache operations
    async def cache_locations(self, service_type: str, locations_data: List[Dict[str, Any]]):
        """Cache location data"""
        try:
            if self.is_sqlite:
                await self._cache_locations_sqlite(service_type, locations_data)
            else:
                await self._cache_locations_postgres(service_type, locations_data)
        except Exception as e:
            logger.error(f"Error caching locations for {service_type}: {e}")
    
    async def get_cached_locations(self, service_type: str, max_age_hours: int = 1) -> Optional[List[Dict[str, Any]]]:
        """Get cached location data"""
        try:
            if self.is_sqlite:
                return await self._get_cached_locations_sqlite(service_type, max_age_hours)
            else:
                return await self._get_cached_locations_postgres(service_type, max_age_hours)
        except Exception as e:
            logger.error(f"Error getting cached locations for {service_type}: {e}")
            return None
    
    async def _cache_locations_sqlite(self, service_type: str, locations_data: List[Dict[str, Any]]):
        """Cache locations in SQLite"""
        import aiosqlite
        
        async with aiosqlite.connect(self.sqlite_path) as db:
            # Delete old data
            await db.execute("DELETE FROM locations_cache WHERE service_type = ?", (service_type,))
            # Insert new data
            await db.execute(
                "INSERT INTO locations_cache (service_type, location_data) VALUES (?, ?)",
                (service_type, json.dumps(locations_data))
            )
            await db.commit()
    
    async def _get_cached_locations_sqlite(self, service_type: str, max_age_hours: int) -> Optional[List[Dict[str, Any]]]:
        """Get cached locations from SQLite"""
        import aiosqlite
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        async with aiosqlite.connect(self.sqlite_path) as db:
            async with db.execute(
                "SELECT location_data FROM locations_cache WHERE service_type = ? AND last_updated > ?",
                (service_type, cutoff_time.isoformat())
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return None
    
    async def _cache_locations_postgres(self, service_type: str, locations_data: List[Dict[str, Any]]):
        """Cache locations in PostgreSQL"""
        async with self.pool.acquire() as conn:
            # Delete old data
            await conn.execute("DELETE FROM locations_cache WHERE service_type = $1", service_type)
            # Insert new data
            await conn.execute(
                "INSERT INTO locations_cache (service_type, location_data) VALUES ($1, $2)",
                service_type, json.dumps(locations_data)
            )
    
    async def _get_cached_locations_postgres(self, service_type: str, max_age_hours: int) -> Optional[List[Dict[str, Any]]]:
        """Get cached locations from PostgreSQL"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT location_data FROM locations_cache WHERE service_type = $1 AND last_updated > $2",
                service_type, cutoff_time
            )
            return json.loads(result["location_data"]) if result else None
    
    # Currency cache operations
    async def cache_currency_rates(self, source: str, rates_data: Dict[str, Any]):
        """Cache currency rates"""
        try:
            if self.is_sqlite:
                await self._cache_currency_sqlite(source, rates_data)
            else:
                await self._cache_currency_postgres(source, rates_data)
        except Exception as e:
            logger.error(f"Error caching currency rates for {source}: {e}")
    
    async def get_cached_currency_rates(self, source: str, max_age_minutes: int = 5) -> Optional[Dict[str, Any]]:
        """Get cached currency rates"""
        try:
            if self.is_sqlite:
                return await self._get_cached_currency_sqlite(source, max_age_minutes)
            else:
                return await self._get_cached_currency_postgres(source, max_age_minutes)
        except Exception as e:
            logger.error(f"Error getting cached currency rates for {source}: {e}")
            return None
    
    async def _cache_currency_sqlite(self, source: str, rates_data: Dict[str, Any]):
        """Cache currency rates in SQLite"""
        import aiosqlite
        
        async with aiosqlite.connect(self.sqlite_path) as db:
            # Delete old data
            await db.execute("DELETE FROM currency_cache WHERE source = ?", (source,))
            # Insert new data
            await db.execute(
                "INSERT INTO currency_cache (source, rates_data) VALUES (?, ?)",
                (source, json.dumps(rates_data))
            )
            await db.commit()
    
    async def _get_cached_currency_sqlite(self, source: str, max_age_minutes: int) -> Optional[Dict[str, Any]]:
        """Get cached currency rates from SQLite"""
        import aiosqlite
        
        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
        
        async with aiosqlite.connect(self.sqlite_path) as db:
            async with db.execute(
                "SELECT rates_data FROM currency_cache WHERE source = ? AND last_updated > ?",
                (source, cutoff_time.isoformat())
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return None
    
    async def _cache_currency_postgres(self, source: str, rates_data: Dict[str, Any]):
        """Cache currency rates in PostgreSQL"""
        async with self.pool.acquire() as conn:
            # Delete old data
            await conn.execute("DELETE FROM currency_cache WHERE source = $1", source)
            # Insert new data
            await conn.execute(
                "INSERT INTO currency_cache (source, rates_data) VALUES ($1, $2)",
                source, json.dumps(rates_data)
            )
    
    async def _get_cached_currency_postgres(self, source: str, max_age_minutes: int) -> Optional[Dict[str, Any]]:
        """Get cached currency rates from PostgreSQL"""
        cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
        
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT rates_data FROM currency_cache WHERE source = $1 AND last_updated > $2",
                source, cutoff_time
            )
            return json.loads(result["rates_data"]) if result else None
    
    # User interaction logging
    async def log_interaction(self, session_id: str, interaction_type: str, data: Dict[str, Any], 
                            user_location: Optional[tuple] = None, language: str = "en"):
        """Log user interaction"""
        try:
            if self.is_sqlite:
                await self._log_interaction_sqlite(session_id, interaction_type, data, user_location, language)
            else:
                await self._log_interaction_postgres(session_id, interaction_type, data, user_location, language)
        except Exception as e:
            logger.error(f"Error logging interaction: {e}")
    
    async def _log_interaction_sqlite(self, session_id: str, interaction_type: str, data: Dict[str, Any],
                                    user_location: Optional[tuple], language: str):
        """Log interaction in SQLite"""
        import aiosqlite
        
        lat, lng = user_location if user_location else (None, None)
        
        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.execute(
                "INSERT INTO user_interactions (session_id, interaction_type, data, user_latitude, user_longitude, language) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, interaction_type, json.dumps(data), lat, lng, language)
            )
            await db.commit()
    
    async def _log_interaction_postgres(self, session_id: str, interaction_type: str, data: Dict[str, Any],
                                      user_location: Optional[tuple], language: str):
        """Log interaction in PostgreSQL"""
        lat, lng = user_location if user_location else (None, None)
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO user_interactions (session_id, interaction_type, data, user_latitude, user_longitude, language) "
                "VALUES ($1, $2, $3, $4, $5, $6)",
                session_id, interaction_type, json.dumps(data), lat, lng, language
            )
    
    # Cleanup operations
    async def cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        try:
            if self.is_sqlite:
                await self._cleanup_expired_cache_sqlite()
            else:
                await self._cleanup_expired_cache_postgres()
            logger.info("Expired cache entries cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {e}")
    
    async def _cleanup_expired_cache_sqlite(self):
        """Clean up expired cache in SQLite"""
        import aiosqlite
        
        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.execute("DELETE FROM cache WHERE expires_at < CURRENT_TIMESTAMP")
            await db.commit()
    
    async def _cleanup_expired_cache_postgres(self):
        """Clean up expired cache in PostgreSQL"""
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM cache WHERE expires_at < CURRENT_TIMESTAMP")

# Global database instance
_db_instance: Optional[Database] = None

async def init_database():
    """Initialize the global database instance"""
    global _db_instance
    _db_instance = Database()
    await _db_instance.initialize()
    
    # Start cleanup task
    asyncio.create_task(periodic_cleanup())

async def get_database() -> Database:
    """Get the global database instance"""
    global _db_instance
    if not _db_instance:
        await init_database()
    return _db_instance

async def close_database():
    """Close the global database instance"""
    global _db_instance
    if _db_instance:
        await _db_instance.close()
        _db_instance = None

async def periodic_cleanup():
    """Periodic cleanup of expired cache entries"""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            db = await get_database()
            await db.cleanup_expired_cache()
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")

# Context manager for database transactions
@asynccontextmanager
async def database_transaction():
    """Context manager for database transactions"""
    db = await get_database()
    
    if db.is_sqlite:
        import aiosqlite
        async with aiosqlite.connect(db.sqlite_path) as conn:
            async with conn:
                yield conn
    else:
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                yield conn