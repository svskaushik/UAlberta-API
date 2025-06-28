"""
Caching utilities for course search optimization.
Provides in-memory and Redis-based caching for frequently searched terms.
"""

import hashlib
import json
import time
from typing import List, Optional, Any, Tuple
from functools import wraps
from collections import OrderedDict
import os

class MemoryCache:
    """Simple in-memory LRU cache for course search results"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
    
    def _generate_key(self, university_id: int, query: str, faculty_code: Optional[str] = None, limit: int = 50) -> str:
        """Generate cache key from search parameters"""
        key_data = {
            'university_id': university_id,
            'query': query.lower().strip(),
            'faculty_code': faculty_code,
            'limit': limit
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, university_id: int, query: str, faculty_code: Optional[str] = None, limit: int = 50) -> Optional[List[Tuple[int, str, str]]]:
        """Get cached search results"""
        key = self._generate_key(university_id, query, faculty_code, limit)
        
        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            
            # Check if cache entry is still valid
            if time.time() - timestamp < self.ttl_seconds:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                return cached_data
            else:
                # Remove expired entry
                del self.cache[key]
        
        return None
    
    def set(self, university_id: int, query: str, results: List[Tuple[int, str, str]], 
            faculty_code: Optional[str] = None, limit: int = 50) -> None:
        """Cache search results"""
        key = self._generate_key(university_id, query, faculty_code, limit)
        
        # Remove oldest entries if cache is full
        while len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        
        self.cache[key] = (results, time.time())
    
    def clear(self) -> None:
        """Clear all cached entries"""
        self.cache.clear()
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_entries = len(self.cache)
        expired_entries = 0
        current_time = time.time()
        
        for cached_data, timestamp in self.cache.values():
            if current_time - timestamp >= self.ttl_seconds:
                expired_entries += 1
        
        return {
            'total_entries': total_entries,
            'expired_entries': expired_entries,
            'active_entries': total_entries - expired_entries,
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds
        }

# Global cache instance
course_search_cache = MemoryCache(
    max_size=int(os.getenv('COURSE_CACHE_SIZE', '1000')),
    ttl_seconds=int(os.getenv('COURSE_CACHE_TTL', '300'))  # 5 minutes default
)

def cached_course_search(cache_enabled: bool = True):
    """Decorator for caching course search results"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, university_id: int, query: str, *args, **kwargs):
            # Extract common parameters - handle both positional and keyword args
            faculty_code = None
            limit = 50
            
            # Handle different method signatures
            if len(args) > 0:
                # If limit is passed as positional argument
                limit = args[0] if len(args) == 1 else args[1]
            if len(args) > 1:
                # If faculty_code is passed as positional argument
                faculty_code = args[0]
                
            # Override with keyword arguments if provided
            faculty_code = kwargs.get('faculty_code', faculty_code)
            limit = kwargs.get('limit', limit)
            
            # Skip cache for very short queries (likely not useful to cache)
            if not cache_enabled or len(query.strip()) < 2:
                return func(self, university_id, query, *args, **kwargs)
            
            # Try to get from cache first
            cached_results = course_search_cache.get(university_id, query, faculty_code, limit)
            if cached_results is not None:
                return cached_results
            
            # Execute the actual search
            results = func(self, university_id, query, *args, **kwargs)
            
            # Cache the results
            course_search_cache.set(university_id, query, results, faculty_code, limit)
            
            return results
        return wrapper
    return decorator

# Redis cache implementation (optional, for production use)
try:
    import redis
    
    class RedisCache:
        """Redis-based cache for distributed environments"""
        
        def __init__(self, redis_url: Optional[str] = None, ttl_seconds: int = 300):
            self.redis_url = redis_url or os.getenv('REDIS_URL')
            self.ttl_seconds = ttl_seconds
            self.redis_client = None
            
            if self.redis_url:
                try:
                    self.redis_client = redis.from_url(self.redis_url)
                    # Test connection
                    self.redis_client.ping()
                except Exception as e:
                    print(f"Warning: Redis connection failed: {e}")
                    self.redis_client = None
        
        def _generate_key(self, university_id: int, query: str, faculty_code: Optional[str] = None, limit: int = 50) -> str:
            key_data = {
                'university_id': university_id,
                'query': query.lower().strip(),
                'faculty_code': faculty_code,
                'limit': limit
            }
            key_string = json.dumps(key_data, sort_keys=True)
            return f"course_search:{hashlib.md5(key_string.encode()).hexdigest()}"
        
        def get(self, university_id: int, query: str, faculty_code: Optional[str] = None, limit: int = 50) -> Optional[List[Tuple[int, str, str]]]:
            if not self.redis_client:
                return None
            
            try:
                key = self._generate_key(university_id, query, faculty_code, limit)
                cached_data = self.redis_client.get(key)
                
                if cached_data:
                    return json.loads(cached_data)
            except Exception as e:
                print(f"Redis get error: {e}")
            
            return None
        
        def set(self, university_id: int, query: str, results: List[Tuple[int, str, str]], 
                faculty_code: Optional[str] = None, limit: int = 50) -> None:
            if not self.redis_client:
                return
            
            try:
                key = self._generate_key(university_id, query, faculty_code, limit)
                self.redis_client.setex(key, self.ttl_seconds, json.dumps(results))
            except Exception as e:
                print(f"Redis set error: {e}")
        
        def clear(self) -> None:
            if not self.redis_client:
                return
            
            try:
                # Clear all course search keys
                keys = self.redis_client.keys("course_search:*")
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                print(f"Redis clear error: {e}")
    
    # Create Redis cache instance if Redis is available
    redis_cache = RedisCache() if os.getenv('REDIS_URL') else None

except ImportError:
    redis_cache = None
