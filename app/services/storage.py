"""
Storage Abstraction Layer - Swappable storage backends
Supports: In-Memory (dev), Redis (production), Supabase (full features)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json


class BaseStorage(ABC):
    """
    Abstract storage interface
    
    All storage implementations must support this interface
    for session management, user progress tracking, etc.
    """
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store a value
        
        Args:
            key: Storage key
            value: Value to store (will be JSON serialized)
            ttl: Time-to-live in seconds (None = no expiry)
        
        Returns:
            True if stored successfully
        """
        pass
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value
        
        Args:
            key: Storage key
        
        Returns:
            Stored value or None if not found
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a value
        
        Args:
            key: Storage key
        
        Returns:
            True if deleted successfully
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if key exists
        
        Args:
            key: Storage key
        
        Returns:
            True if key exists
        """
        pass
    
    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """
        List keys matching pattern
        
        Args:
            pattern: Key pattern (supports wildcards)
        
        Returns:
            List of matching keys
        """
        pass


class InMemoryStorage(BaseStorage):
    """
    In-memory storage for development/testing
    
    WARNING: Data is lost when process restarts
    Does NOT work across multiple containers
    Use only for local development
    """
    
    def __init__(self):
        self._store: Dict[str, tuple] = {}  # {key: (value, expiry)}
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Store value in memory"""
        expiry = None
        if ttl:
            expiry = datetime.now() + timedelta(seconds=ttl)
        
        # Serialize to JSON for consistency with other backends
        serialized = json.dumps(value)
        self._store[key] = (serialized, expiry)
        return True
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from memory"""
        if key not in self._store:
            return None
        
        value, expiry = self._store[key]
        
        # Check expiry
        if expiry and datetime.now() > expiry:
            del self._store[key]
            return None
        
        # Deserialize from JSON
        return json.loads(value)
    
    async def delete(self, key: str) -> bool:
        """Delete value from memory"""
        if key in self._store:
            del self._store[key]
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if key not in self._store:
            return False
        
        # Check expiry
        _, expiry = self._store[key]
        if expiry and datetime.now() > expiry:
            del self._store[key]
            return False
        
        return True
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """List all keys (simple pattern matching)"""
        # Simple wildcard support
        if pattern == "*":
            return list(self._store.keys())
        
        # Pattern matching (simplified)
        import re
        regex_pattern = pattern.replace("*", ".*")
        regex = re.compile(regex_pattern)
        
        return [key for key in self._store.keys() if regex.match(key)]


class RedisStorage(BaseStorage):
    """
    Redis storage for production
    
    Features:
    - Persistent across container restarts
    - Works with horizontal scaling
    - TTL support
    - High performance
    
    Requires: redis[asyncio]
    """
    
    def __init__(self, redis_url: str):
        """
        Initialize Redis storage
        
        Args:
            redis_url: Redis connection URL
                      e.g., 'redis://localhost:6379'
                      or 'redis://user:pass@host:6379/0'
        """
        try:
            import redis.asyncio as aioredis
            self.redis = aioredis.from_url(redis_url, decode_responses=True)
        except ImportError:
            raise ImportError(
                "Redis not installed. Install with: pip install redis[asyncio]"
            )
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Store value in Redis"""
        serialized = json.dumps(value)
        
        if ttl:
            await self.redis.setex(key, ttl, serialized)
        else:
            await self.redis.set(key, serialized)
        
        return True
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from Redis"""
        value = await self.redis.get(key)
        
        if value is None:
            return None
        
        return json.loads(value)
    
    async def delete(self, key: str) -> bool:
        """Delete value from Redis"""
        result = await self.redis.delete(key)
        return result > 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        return await self.redis.exists(key) > 0
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """List keys matching pattern"""
        return await self.redis.keys(pattern)
    
    async def close(self):
        """Close Redis connection"""
        await self.redis.close()


class SupabaseStorage(BaseStorage):
    """
    Supabase storage for full-featured persistence
    
    Features:
    - PostgreSQL backend (full SQL)
    - Real-time subscriptions
    - User authentication integration
    - Historical data queries
    
    Requires: supabase
    """
    
    def __init__(self, supabase_url: str, supabase_key: str):
        """
        Initialize Supabase storage
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
        """
        try:
            from supabase import create_client, Client
            self.client: Client = create_client(supabase_url, supabase_key)
            self.table = "reading_sessions"  # Default table name
        except ImportError:
            raise ImportError(
                "Supabase not installed. Install with: pip install supabase"
            )
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Store value in Supabase"""
        data = {
            "key": key,
            "value": json.dumps(value),
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(seconds=ttl)).isoformat() if ttl else None
        }
        
        # Upsert (insert or update)
        self.client.table(self.table).upsert(data).execute()
        return True
    
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from Supabase"""
        result = self.client.table(self.table) \
            .select("value, expires_at") \
            .eq("key", key) \
            .execute()
        
        if not result.data:
            return None
        
        row = result.data[0]
        
        # Check expiry
        if row['expires_at']:
            expires = datetime.fromisoformat(row['expires_at'])
            if datetime.now() > expires:
                await self.delete(key)
                return None
        
        return json.loads(row['value'])
    
    async def delete(self, key: str) -> bool:
        """Delete value from Supabase"""
        self.client.table(self.table).delete().eq("key", key).execute()
        return True
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Supabase"""
        result = self.client.table(self.table) \
            .select("key") \
            .eq("key", key) \
            .execute()
        
        return len(result.data) > 0
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """List keys matching pattern"""
        # Supabase uses SQL LIKE
        sql_pattern = pattern.replace("*", "%")
        
        result = self.client.table(self.table) \
            .select("key") \
            .like("key", sql_pattern) \
            .execute()
        
        return [row['key'] for row in result.data]


class StorageFactory:
    """Factory for creating storage instances"""
    
    @staticmethod
    def create_storage(storage_type: str, config: Dict[str, Any]) -> BaseStorage:
        """
        Create storage instance
        
        Args:
            storage_type: 'memory', 'redis', or 'supabase'
            config: Storage-specific configuration
        
        Returns:
            Initialized storage instance
        """
        if storage_type == "memory":
            return InMemoryStorage()
        
        elif storage_type == "redis":
            redis_url = config.get('redis_url', 'redis://localhost:6379')
            return RedisStorage(redis_url)
        
        elif storage_type == "supabase":
            supabase_url = config['supabase_url']
            supabase_key = config['supabase_key']
            return SupabaseStorage(supabase_url, supabase_key)
        
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")


# Example usage:
"""
# Development (in-memory)
storage = StorageFactory.create_storage('memory', {})

# Production (Redis)
storage = StorageFactory.create_storage('redis', {
    'redis_url': os.getenv('REDIS_URL')
})

# Full-featured (Supabase)
storage = StorageFactory.create_storage('supabase', {
    'supabase_url': os.getenv('SUPABASE_URL'),
    'supabase_key': os.getenv('SUPABASE_KEY')
})

# Use storage
await storage.set('session:123', {'user_id': 'abc', 'progress': 5}, ttl=3600)
data = await storage.get('session:123')
"""
