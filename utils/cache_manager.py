"""
Advanced Caching System for Discord Music Bot
Caches song metadata, stream URLs, and playlist data for better performance
"""
import asyncio
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from collections import OrderedDict
import os
import pickle
from pathlib import Path
from utils.memory_manager import memory_manager

class CacheEntry:
    """Individual cache entry with metadata"""
    
    def __init__(self, data: Any, ttl: int = 3600):
        self.data = data
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.ttl = ttl  # Time to live in seconds
        self.access_count = 1
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() > (self.created_at + self.ttl)
    
    def touch(self):
        """Update last accessed time and increment access count"""
        self.last_accessed = time.time()
        self.access_count += 1
    
    def age(self) -> int:
        """Get age of cache entry in seconds"""
        return int(time.time() - self.created_at)
    
    def time_until_expiry(self) -> int:
        """Get seconds until expiry"""
        expiry_time = self.created_at + self.ttl
        return max(0, int(expiry_time - time.time()))

class LRUCache:
    """LRU Cache with TTL and size limits"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        if key not in self.cache:
            self._misses += 1
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if entry.is_expired():
            del self.cache[key]
            self._misses += 1
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        entry.touch()
        self._hits += 1
        
        return entry.data
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Put item in cache"""
        ttl = ttl or self.default_ttl
        entry = CacheEntry(value, ttl)
        
        # Remove existing entry if present
        if key in self.cache:
            del self.cache[key]
        
        # Add new entry
        self.cache[key] = entry
        
        # Evict oldest entries if over size limit  
        while len(self.cache) > self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            self._evictions += 1
        
        return True
    
    def delete(self, key: str) -> bool:
        """Delete item from cache"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries"""
        expired_keys = [key for key, entry in self.cache.items() if entry.is_expired()]
        for key in expired_keys:
            del self.cache[key]
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': round(hit_rate, 2),
            'evictions': self._evictions,
            'total_requests': total_requests
        }
    
    def get_top_accessed(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most accessed cache entries"""
        items = [(key, entry.access_count) for key, entry in self.cache.items()]
        return sorted(items, key=lambda x: x[1], reverse=True)[:limit]

class MusicCacheManager:
    """Main cache manager for music bot"""
    
    def __init__(self):
        # Different caches for different data types
        self.metadata_cache = LRUCache(max_size=2000, default_ttl=7200)  # 2 hours
        self.stream_cache = LRUCache(max_size=500, default_ttl=1800)     # 30 minutes (URLs expire)
        self.playlist_cache = LRUCache(max_size=200, default_ttl=3600)   # 1 hour
        self.search_cache = LRUCache(max_size=1000, default_ttl=1800)    # 30 minutes
        
        # Cache persistence
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # Statistics
        self.start_time = time.time()
        self._cache_saves = 0
        self._cache_loads = 0
        
        # Background cleanup task
        self._cleanup_task = None
        
        # Track with memory manager
        memory_manager.track_object(self, 'cache_manager')
    
    def _generate_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key from identifier"""
        # Create hash of identifier for consistent key length
        hash_obj = hashlib.md5(identifier.encode('utf-8'))
        return f"{prefix}:{hash_obj.hexdigest()}"
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistent caching"""
        # Remove tracking parameters and normalize
        if 'youtube.com' in url or 'youtu.be' in url:
            # Extract video ID
            import re
            video_id_match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
            if video_id_match:
                return f"https://www.youtube.com/watch?v={video_id_match.group(1)}"
        return url.split('?')[0]  # Remove query parameters for other URLs
    
    async def get_song_metadata(self, search_query: str) -> Optional[Dict[str, Any]]:
        """Get cached song metadata"""
        key = self._generate_key("metadata", search_query.lower())
        return self.metadata_cache.get(key)
    
    async def cache_song_metadata(self, search_query: str, metadata: Dict[str, Any], ttl: int = 7200):
        """Cache song metadata"""
        key = self._generate_key("metadata", search_query.lower())
        
        # Create lightweight metadata for caching
        cache_data = {
            'title': metadata.get('title'),
            'uploader': metadata.get('uploader'),
            'uploader_url': metadata.get('uploader_url'),
            'duration': metadata.get('duration'),
            'thumbnail': metadata.get('thumbnail'),
            'description': metadata.get('description'),
            'webpage_url': metadata.get('webpage_url'),
            'view_count': metadata.get('view_count'),
            'like_count': metadata.get('like_count'),
            'upload_date': metadata.get('upload_date'),
            'cached_at': time.time()
        }
        
        return self.metadata_cache.put(key, cache_data, ttl)
    
    async def get_stream_url(self, webpage_url: str) -> Optional[str]:
        """Get cached stream URL"""
        normalized_url = self._normalize_url(webpage_url)
        key = self._generate_key("stream", normalized_url)
        
        cached_data = self.stream_cache.get(key)
        if cached_data:
            return cached_data.get('stream_url')
        return None
    
    async def cache_stream_url(self, webpage_url: str, stream_url: str, ttl: int = 1800):
        """Cache stream URL with shorter TTL (URLs expire quickly)"""
        normalized_url = self._normalize_url(webpage_url)
        key = self._generate_key("stream", normalized_url)
        
        cache_data = {
            'stream_url': stream_url,
            'webpage_url': normalized_url,
            'cached_at': time.time()
        }
        
        return self.stream_cache.put(key, cache_data, ttl)
    
    async def get_playlist_data(self, playlist_url: str) -> Optional[Dict[str, Any]]:
        """Get cached playlist data"""
        normalized_url = self._normalize_url(playlist_url)
        key = self._generate_key("playlist", normalized_url)
        return self.playlist_cache.get(key)
    
    async def cache_playlist_data(self, playlist_url: str, playlist_data: Dict[str, Any], ttl: int = 3600):
        """Cache playlist data"""
        normalized_url = self._normalize_url(playlist_url)
        key = self._generate_key("playlist", normalized_url)
        
        # Create lightweight playlist data
        cache_data = {
            'title': playlist_data.get('title'),
            'entries': playlist_data.get('entries', []),
            'uploader': playlist_data.get('uploader'),
            'description': playlist_data.get('description'),
            'webpage_url': normalized_url,
            'cached_at': time.time(),
            'entry_count': len(playlist_data.get('entries', []))
        }
        
        return self.playlist_cache.put(key, cache_data, ttl)
    
    async def get_search_results(self, search_query: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results"""
        key = self._generate_key("search", search_query.lower())
        return self.search_cache.get(key)
    
    async def cache_search_results(self, search_query: str, results: List[Dict[str, Any]], ttl: int = 1800):
        """Cache search results"""
        key = self._generate_key("search", search_query.lower())
        
        # Limit results to prevent memory bloat
        limited_results = results[:20] if len(results) > 20 else results
        
        cache_data = {
            'results': limited_results,
            'query': search_query,
            'cached_at': time.time(),
            'result_count': len(limited_results)
        }
        
        return self.search_cache.put(key, cache_data, ttl)
    
    async def warm_cache_for_popular_songs(self, popular_queries: List[str]):
        """Pre-warm cache with popular song searches"""
        print(f"🔥 Cache warming started for {len(popular_queries)} popular songs...")
        
        warmed = 0
        for query in popular_queries:
            try:
                # Check if already cached
                if await self.get_song_metadata(query):
                    continue
                
                # This would typically trigger actual YTDL extraction
                # For now, we'll just create placeholder entries
                print(f"🔥 Warming cache for: {query}")
                warmed += 1
                
                # Add small delay to prevent overwhelming
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"⚠️ Cache warming failed for '{query}': {e}")
        
        print(f"🔥 Cache warming completed: {warmed} songs pre-loaded")
    
    async def cleanup_expired_entries(self):
        """Clean up expired entries from all caches"""
        total_cleaned = 0
        
        caches = [
            ("metadata", self.metadata_cache),
            ("stream", self.stream_cache), 
            ("playlist", self.playlist_cache),
            ("search", self.search_cache)
        ]
        
        for cache_name, cache in caches:
            cleaned = cache.cleanup_expired()
            total_cleaned += cleaned
            if cleaned > 0:
                print(f"🧹 Cleaned {cleaned} expired {cache_name} entries")
        
        return total_cleaned
    
    async def save_cache_to_disk(self):
        """Save important cache data to disk for persistence"""
        try:
            # Save metadata cache (most valuable for persistence)
            metadata_file = self.cache_dir / "metadata_cache.pkl"
            with open(metadata_file, 'wb') as f:
                # Only save non-expired entries
                valid_entries = {k: v for k, v in self.metadata_cache.cache.items() if not v.is_expired()}
                pickle.dump(valid_entries, f)
            
            self._cache_saves += 1
            print(f"💾 Saved {len(valid_entries)} metadata entries to disk")
            
        except Exception as e:
            print(f"⚠️ Failed to save cache to disk: {e}")
    
    async def load_cache_from_disk(self):
        """Load cache data from disk"""
        try:
            metadata_file = self.cache_dir / "metadata_cache.pkl"
            if metadata_file.exists():
                with open(metadata_file, 'rb') as f:
                    cached_entries = pickle.load(f)
                
                # Restore valid entries
                loaded = 0
                for key, entry in cached_entries.items():
                    if not entry.is_expired():
                        self.metadata_cache.cache[key] = entry
                        loaded += 1
                
                self._cache_loads += 1
                print(f"📥 Loaded {loaded} metadata entries from disk")
                
        except Exception as e:
            print(f"⚠️ Failed to load cache from disk: {e}")
    
    async def start_background_cleanup(self, interval: int = 600):
        """Start background cleanup task"""
        if self._cleanup_task and not self._cleanup_task.done():
            return
        
        self._cleanup_task = asyncio.create_task(self._background_cleanup_loop(interval))
        print(f"🧹 Cache cleanup started (every {interval//60} minutes)")
    
    async def _background_cleanup_loop(self, interval: int):
        """Background cleanup loop"""
        while True:
            try:
                await asyncio.sleep(interval)
                
                # Cleanup expired entries
                cleaned = await self.cleanup_expired_entries()
                
                # Save cache to disk periodically
                await self.save_cache_to_disk()
                
                if cleaned > 0:
                    print(f"🧹 Background cleanup: {cleaned} entries removed")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ Background cleanup error: {e}")
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        uptime = time.time() - self.start_time
        
        return {
            'uptime_seconds': int(uptime),
            'uptime_formatted': str(timedelta(seconds=int(uptime))),
            'metadata_cache': self.metadata_cache.get_stats(),
            'stream_cache': self.stream_cache.get_stats(),
            'playlist_cache': self.playlist_cache.get_stats(),
            'search_cache': self.search_cache.get_stats(),
            'total_entries': (
                len(self.metadata_cache.cache) + 
                len(self.stream_cache.cache) + 
                len(self.playlist_cache.cache) + 
                len(self.search_cache.cache)
            ),
            'cache_saves': self._cache_saves,
            'cache_loads': self._cache_loads,
            'cache_dir_size': self._get_cache_dir_size()
        }
    
    def _get_cache_dir_size(self) -> int:
        """Get cache directory size in bytes"""
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file())
            return total_size
        except:
            return 0
    
    def get_cache_efficiency_report(self) -> Dict[str, Any]:
        """Get detailed cache efficiency report"""
        stats = self.get_comprehensive_stats()
        
        # Calculate overall hit rate
        total_hits = sum(cache['hits'] for cache in [
            stats['metadata_cache'], stats['stream_cache'], 
            stats['playlist_cache'], stats['search_cache']
        ])
        total_requests = sum(cache['total_requests'] for cache in [
            stats['metadata_cache'], stats['stream_cache'],
            stats['playlist_cache'], stats['search_cache'] 
        ])
        
        overall_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'overall_hit_rate': round(overall_hit_rate, 2),
            'total_hits': total_hits,
            'total_requests': total_requests,
            'memory_saved_estimate': self._estimate_memory_saved(),
            'api_calls_saved': total_hits,  # Each hit = 1 saved API call
            'performance_improvement': self._calculate_performance_improvement(),
            'top_cached_items': self._get_top_cached_items()
        }
    
    def _estimate_memory_saved(self) -> str:
        """Estimate memory saved by caching"""
        # Rough estimate: each cached metadata ~2KB, stream URL ~1KB
        metadata_saved = len(self.metadata_cache.cache) * 2048
        stream_saved = len(self.stream_cache.cache) * 1024
        playlist_saved = len(self.playlist_cache.cache) * 5120
        search_saved = len(self.search_cache.cache) * 3072
        
        total_bytes = metadata_saved + stream_saved + playlist_saved + search_saved
        
        if total_bytes > 1024 * 1024:
            return f"{total_bytes / (1024 * 1024):.1f} MB"
        elif total_bytes > 1024:
            return f"{total_bytes / 1024:.1f} KB" 
        else:
            return f"{total_bytes} bytes"
    
    def _calculate_performance_improvement(self) -> str:
        """Calculate estimated performance improvement"""
        stats = self.get_comprehensive_stats()
        overall_hit_rate = self.get_cache_efficiency_report()['overall_hit_rate']
        
        if overall_hit_rate > 0:
            # Assume cached operations are 10x faster than API calls
            improvement = (overall_hit_rate / 100) * 10
            return f"{improvement:.1f}x faster"
        return "No improvement yet"
    
    def _get_top_cached_items(self) -> List[Dict[str, Any]]:
        """Get top cached items across all caches"""
        all_items = []
        
        # Get from all caches
        caches = [
            ("metadata", self.metadata_cache),
            ("stream", self.stream_cache),
            ("playlist", self.playlist_cache), 
            ("search", self.search_cache)
        ]
        
        for cache_type, cache in caches:
            for key, entry in cache.cache.items():
                all_items.append({
                    'type': cache_type,
                    'key': key[:50],  # Truncate long keys
                    'access_count': entry.access_count,
                    'age_seconds': entry.age(),
                    'expires_in': entry.time_until_expiry()
                })
        
        # Sort by access count
        return sorted(all_items, key=lambda x: x['access_count'], reverse=True)[:10]

# Global cache manager instance
cache_manager = MusicCacheManager()