"""
Database Manager for Discord Music Bot
Handles guild settings, user statistics, music analytics, and bot metrics using SQLite
"""
import sqlite3
import json
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import time
from contextlib import asynccontextmanager
from utils.memory_manager import memory_manager

class DatabaseManager:
    """Comprehensive database management for the music bot"""
    
    def __init__(self, db_path: str = "data/bot_database.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
        # Connection pool settings
        self._connection_pool = []
        self._pool_size = 5
        self._connection_timeout = 30
        
        # Cache for frequently accessed data
        self._guild_settings_cache = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps = {}
        
        # Statistics tracking
        self.db_operations = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Track with memory manager
        memory_manager.track_object(self, 'database_manager')
    
    async def initialize_database(self):
        """Initialize database with all required tables"""
        print("🗄️ Initializing database...")
        
        async with aiosqlite.connect(self.db_path) as db:
            # Enable foreign keys
            await db.execute("PRAGMA foreign_keys = ON")
            
            # Guild settings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    guild_name TEXT NOT NULL,
                    custom_prefix TEXT DEFAULT '?',
                    default_volume REAL DEFAULT 0.5,
                    auto_disconnect_delay INTEGER DEFAULT 300,
                    max_queue_size INTEGER DEFAULT 100,
                    allow_playlists BOOLEAN DEFAULT TRUE,
                    dj_role_id INTEGER DEFAULT NULL,
                    music_channel_id INTEGER DEFAULT NULL,
                    language TEXT DEFAULT 'EN',
                    settings_json TEXT DEFAULT '{}',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User statistics table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_statistics (
                    user_id INTEGER,
                    guild_id INTEGER,
                    username TEXT NOT NULL,
                    total_songs_played INTEGER DEFAULT 0,
                    total_listening_time INTEGER DEFAULT 0,
                    favorite_genre TEXT DEFAULT NULL,
                    last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
                    commands_used INTEGER DEFAULT 0,
                    playlists_created INTEGER DEFAULT 0,
                    settings_json TEXT DEFAULT '{}',
                    PRIMARY KEY (user_id, guild_id),
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id)
                )
            """)
            
            # Music analytics table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS music_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    song_title TEXT NOT NULL,
                    song_url TEXT NOT NULL,
                    artist TEXT DEFAULT NULL,
                    duration INTEGER DEFAULT 0,
                    play_count INTEGER DEFAULT 1,
                    unique_users INTEGER DEFAULT 1,
                    last_played DATETIME DEFAULT CURRENT_TIMESTAMP,
                    source_platform TEXT DEFAULT 'youtube',
                    analytics_json TEXT DEFAULT '{}',
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id)
                )
            """)
            
            # Bot performance metrics table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bot_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_type TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    guild_id INTEGER DEFAULT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata_json TEXT DEFAULT '{}',
                    FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id)
                )
            """)
            
            # Error logs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    guild_id INTEGER DEFAULT NULL,
                    user_id INTEGER DEFAULT NULL,
                    command_name TEXT DEFAULT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    stack_trace TEXT DEFAULT NULL,
                    resolved BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Cache persistence table  
            await db.execute("""
                CREATE TABLE IF NOT EXISTS cache_persistence (
                    cache_key TEXT PRIMARY KEY,
                    cache_type TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    expires_at DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1
                )
            """)
            
            # Create indexes for better performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_guild_settings_guild_id ON guild_settings(guild_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_user_stats_guild_user ON user_statistics(guild_id, user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_music_analytics_guild ON music_analytics(guild_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_music_analytics_song ON music_analytics(song_url)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_bot_metrics_type ON bot_metrics(metric_type)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_timestamp ON error_logs(timestamp)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_persistence(expires_at)")
            
            await db.commit()
            
        print("✅ Database initialized successfully")
        
        # Clean up expired cache entries
        await self.cleanup_expired_cache()
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection with proper resource management"""
        conn = None
        try:
            conn = await aiosqlite.connect(self.db_path, timeout=self._connection_timeout)
            await conn.execute("PRAGMA foreign_keys = ON")
            self.db_operations += 1
            yield conn
        finally:
            if conn:
                await conn.close()
    
    # Guild Settings Management
    async def get_guild_settings(self, guild_id: int, guild_name: str = None) -> Dict[str, Any]:
        """Get guild settings with caching"""
        
        # Check cache first
        cache_key = f"guild_{guild_id}"
        if cache_key in self._guild_settings_cache:
            if time.time() - self._cache_timestamps.get(cache_key, 0) < self._cache_ttl:
                self.cache_hits += 1
                return self._guild_settings_cache[cache_key]
        
        self.cache_misses += 1
        
        async with self.get_connection() as db:
            cursor = await db.execute("""
                SELECT * FROM guild_settings WHERE guild_id = ?
            """, (guild_id,))
            row = await cursor.fetchone()
            
            if row:
                # Convert row to dict
                columns = [desc[0] for desc in cursor.description]
                settings = dict(zip(columns, row))
                
                # Parse JSON settings
                try:
                    settings['settings_json'] = json.loads(settings.get('settings_json', '{}'))
                except json.JSONDecodeError:
                    settings['settings_json'] = {}
                
            else:
                # Create default settings for new guild
                if guild_name:
                    await self.create_guild_settings(guild_id, guild_name)
                    return await self.get_guild_settings(guild_id, guild_name)
                else:
                    # Return default settings without creating
                    settings = {
                        'guild_id': guild_id,
                        'guild_name': 'Unknown',
                        'custom_prefix': '?',
                        'default_volume': 0.5,
                        'auto_disconnect_delay': 300,
                        'max_queue_size': 100,
                        'allow_playlists': True,
                        'dj_role_id': None,
                        'music_channel_id': None,
                        'language': 'EN',
                        'settings_json': {}
                    }
        
        # Cache the settings
        self._guild_settings_cache[cache_key] = settings
        self._cache_timestamps[cache_key] = time.time()
        
        return settings
    
    async def create_guild_settings(self, guild_id: int, guild_name: str) -> bool:
        """Create default guild settings"""
        try:
            async with self.get_connection() as db:
                await db.execute("""
                    INSERT OR REPLACE INTO guild_settings 
                    (guild_id, guild_name, updated_at) 
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (guild_id, guild_name))
                await db.commit()
                
                # Clear cache
                cache_key = f"guild_{guild_id}"
                self._guild_settings_cache.pop(cache_key, None)
                self._cache_timestamps.pop(cache_key, None)
                
                return True
        except Exception as e:
            print(f"❌ Failed to create guild settings: {e}")
            return False
    
    async def update_guild_setting(self, guild_id: int, setting_name: str, setting_value: Any) -> bool:
        """Update a specific guild setting"""
        try:
            async with self.get_connection() as db:
                if setting_name in ['custom_prefix', 'default_volume', 'auto_disconnect_delay', 
                                   'max_queue_size', 'allow_playlists', 'dj_role_id', 
                                   'music_channel_id', 'language']:
                    # Direct column update
                    await db.execute(f"""
                        UPDATE guild_settings 
                        SET {setting_name} = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE guild_id = ?
                    """, (setting_value, guild_id))
                else:
                    # JSON settings update
                    cursor = await db.execute("""
                        SELECT settings_json FROM guild_settings WHERE guild_id = ?
                    """, (guild_id,))
                    row = await cursor.fetchone()
                    
                    if row:
                        try:
                            settings_json = json.loads(row[0] or '{}')
                        except json.JSONDecodeError:
                            settings_json = {}
                        
                        settings_json[setting_name] = setting_value
                        
                        await db.execute("""
                            UPDATE guild_settings 
                            SET settings_json = ?, updated_at = CURRENT_TIMESTAMP 
                            WHERE guild_id = ?
                        """, (json.dumps(settings_json), guild_id))
                
                await db.commit()
                
                # Clear cache
                cache_key = f"guild_{guild_id}"
                self._guild_settings_cache.pop(cache_key, None)
                self._cache_timestamps.pop(cache_key, None)
                
                return True
        except Exception as e:
            print(f"❌ Failed to update guild setting: {e}")
            return False
    
    # User Statistics Management
    async def track_user_activity(self, user_id: int, guild_id: int, username: str, 
                                 activity_type: str, metadata: Dict[str, Any] = None):
        """Track user activity and update statistics"""
        try:
            async with self.get_connection() as db:
                # Get or create user stats
                cursor = await db.execute("""
                    SELECT * FROM user_statistics WHERE user_id = ? AND guild_id = ?
                """, (user_id, guild_id))
                row = await cursor.fetchone()
                
                if not row:
                    # Create new user entry
                    await db.execute("""
                        INSERT INTO user_statistics 
                        (user_id, guild_id, username, commands_used, last_active)
                        VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                    """, (user_id, guild_id, username))
                else:
                    # Update existing entry
                    updates = {
                        'commands_used': 'commands_used + 1',
                        'last_active': 'CURRENT_TIMESTAMP'
                    }
                    
                    if activity_type == 'song_played':
                        updates['total_songs_played'] = 'total_songs_played + 1'
                        if metadata and 'duration' in metadata:
                            updates['total_listening_time'] = f'total_listening_time + {metadata["duration"]}'
                    elif activity_type == 'playlist_created':
                        updates['playlists_created'] = 'playlists_created + 1'
                    
                    set_clause = ', '.join(f"{k} = {v}" for k, v in updates.items())
                    await db.execute(f"""
                        UPDATE user_statistics 
                        SET {set_clause}
                        WHERE user_id = ? AND guild_id = ?
                    """, (user_id, guild_id))
                
                await db.commit()
        except Exception as e:
            print(f"❌ Failed to track user activity: {e}")
    
    async def get_user_statistics(self, user_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get user statistics"""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute("""
                    SELECT * FROM user_statistics WHERE user_id = ? AND guild_id = ?
                """, (user_id, guild_id))
                row = await cursor.fetchone()
                
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    stats = dict(zip(columns, row))
                    
                    # Parse JSON settings
                    try:
                        stats['settings_json'] = json.loads(stats.get('settings_json', '{}'))
                    except json.JSONDecodeError:
                        stats['settings_json'] = {}
                    
                    return stats
                return None
        except Exception as e:
            print(f"❌ Failed to get user statistics: {e}")
            return None
    
    # Music Analytics
    async def track_song_play(self, guild_id: int, song_title: str, song_url: str, 
                             artist: str = None, duration: int = 0, user_id: int = None):
        """Track song play for analytics"""
        try:
            async with self.get_connection() as db:
                # Check if song exists
                cursor = await db.execute("""
                    SELECT id, play_count, unique_users FROM music_analytics 
                    WHERE guild_id = ? AND song_url = ?
                """, (guild_id, song_url))
                row = await cursor.fetchone()
                
                if row:
                    # Update existing record
                    song_id, play_count, unique_users = row
                    await db.execute("""
                        UPDATE music_analytics 
                        SET play_count = play_count + 1, last_played = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (song_id,))
                else:
                    # Create new record
                    await db.execute("""
                        INSERT INTO music_analytics 
                        (guild_id, song_title, song_url, artist, duration, source_platform)
                        VALUES (?, ?, ?, ?, ?, 'youtube')
                    """, (guild_id, song_title, song_url, artist or 'Unknown', duration))
                
                await db.commit()
                
                # Track user activity
                if user_id:
                    await self.track_user_activity(
                        user_id, guild_id, 'Unknown', 'song_played', 
                        {'duration': duration}
                    )
                
        except Exception as e:
            print(f"❌ Failed to track song play: {e}")
    
    async def get_popular_songs(self, guild_id: int = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular songs"""
        try:
            async with self.get_connection() as db:
                if guild_id:
                    cursor = await db.execute("""
                        SELECT song_title, artist, play_count, last_played 
                        FROM music_analytics 
                        WHERE guild_id = ? 
                        ORDER BY play_count DESC, last_played DESC 
                        LIMIT ?
                    """, (guild_id, limit))
                else:
                    cursor = await db.execute("""
                        SELECT song_title, artist, SUM(play_count) as total_plays,
                               MAX(last_played) as last_played
                        FROM music_analytics 
                        GROUP BY song_url, song_title
                        ORDER BY total_plays DESC, last_played DESC 
                        LIMIT ?
                    """, (limit,))
                
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"❌ Failed to get popular songs: {e}")
            return []
    
    # Bot Performance Metrics
    async def record_metric(self, metric_type: str, metric_value: float, 
                           guild_id: int = None, metadata: Dict[str, Any] = None):
        """Record performance metric"""
        try:
            async with self.get_connection() as db:
                await db.execute("""
                    INSERT INTO bot_metrics 
                    (metric_type, metric_value, guild_id, metadata_json)
                    VALUES (?, ?, ?, ?)
                """, (metric_type, metric_value, guild_id, json.dumps(metadata or {})))
                await db.commit()
        except Exception as e:
            print(f"❌ Failed to record metric: {e}")
    
    async def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary for the last N hours"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            async with self.get_connection() as db:
                # Get metric averages
                cursor = await db.execute("""
                    SELECT metric_type, AVG(metric_value) as avg_value, 
                           COUNT(*) as count, MAX(timestamp) as last_recorded
                    FROM bot_metrics 
                    WHERE timestamp >= ?
                    GROUP BY metric_type
                """, (since,))
                
                metrics = {}
                async for row in cursor:
                    metrics[row[0]] = {
                        'average': round(row[1], 2),
                        'count': row[2],
                        'last_recorded': row[3]
                    }
                
                return metrics
        except Exception as e:
            print(f"❌ Failed to get metrics summary: {e}")
            return {}
    
    # Error Logging
    async def log_error(self, error_type: str, error_message: str, guild_id: int = None,
                       user_id: int = None, command_name: str = None, stack_trace: str = None):
        """Log error to database"""
        try:
            async with self.get_connection() as db:
                await db.execute("""
                    INSERT INTO error_logs 
                    (error_type, error_message, guild_id, user_id, command_name, stack_trace)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (error_type, error_message, guild_id, user_id, command_name, stack_trace))
                await db.commit()
        except Exception as e:
            print(f"❌ Failed to log error: {e}")
    
    async def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the last N hours"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            async with self.get_connection() as db:
                cursor = await db.execute("""
                    SELECT error_type, COUNT(*) as count, MAX(timestamp) as last_occurred
                    FROM error_logs 
                    WHERE timestamp >= ?
                    GROUP BY error_type
                    ORDER BY count DESC
                """, (since,))
                
                errors = {}
                total_errors = 0
                async for row in cursor:
                    errors[row[0]] = {
                        'count': row[1],
                        'last_occurred': row[2]
                    }
                    total_errors += row[1]
                
                return {
                    'total_errors': total_errors,
                    'by_type': errors,
                    'period_hours': hours
                }
        except Exception as e:
            print(f"❌ Failed to get error summary: {e}")
            return {'total_errors': 0, 'by_type': {}, 'period_hours': hours}
    
    # Cache Persistence
    async def save_cache_data(self, cache_key: str, cache_type: str, data: Any, expires_at: datetime):
        """Save cache data to database for persistence"""
        try:
            async with self.get_connection() as db:
                await db.execute("""
                    INSERT OR REPLACE INTO cache_persistence 
                    (cache_key, cache_type, data_json, expires_at, access_count)
                    VALUES (?, ?, ?, ?, COALESCE((SELECT access_count FROM cache_persistence WHERE cache_key = ?), 0) + 1)
                """, (cache_key, cache_type, json.dumps(data), expires_at, cache_key))
                await db.commit()
        except Exception as e:
            print(f"❌ Failed to save cache data: {e}")
    
    async def load_cache_data(self, cache_type: str = None) -> List[Dict[str, Any]]:
        """Load cache data from database"""
        try:
            async with self.get_connection() as db:
                if cache_type:
                    cursor = await db.execute("""
                        SELECT cache_key, data_json, expires_at, access_count 
                        FROM cache_persistence 
                        WHERE cache_type = ? AND expires_at > CURRENT_TIMESTAMP
                    """, (cache_type,))
                else:
                    cursor = await db.execute("""
                        SELECT cache_key, cache_type, data_json, expires_at, access_count 
                        FROM cache_persistence 
                        WHERE expires_at > CURRENT_TIMESTAMP
                    """)
                
                cache_entries = []
                async for row in cursor:
                    try:
                        data = json.loads(row[2])  # data_json is at index 2
                        cache_entries.append({
                            'cache_key': row[0],
                            'cache_type': row[1] if not cache_type else cache_type,
                            'data': data,
                            'expires_at': row[3 if not cache_type else 2],
                            'access_count': row[4 if not cache_type else 3]
                        })
                    except json.JSONDecodeError:
                        continue
                
                return cache_entries
        except Exception as e:
            print(f"❌ Failed to load cache data: {e}")
            return []
    
    async def cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute("DELETE FROM cache_persistence WHERE expires_at <= CURRENT_TIMESTAMP")
                deleted = cursor.rowcount
                await db.commit()
                
                if deleted > 0:
                    print(f"🧹 Cleaned up {deleted} expired cache entries from database")
                
                return deleted
        except Exception as e:
            print(f"❌ Failed to cleanup expired cache: {e}")
            return 0
    
    # Database Maintenance
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            async with self.get_connection() as db:
                stats = {}
                
                # Table row counts
                tables = ['guild_settings', 'user_statistics', 'music_analytics', 
                         'bot_metrics', 'error_logs', 'cache_persistence']
                
                for table in tables:
                    cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
                    count = (await cursor.fetchone())[0]
                    stats[f"{table}_count"] = count
                
                # Database size
                cursor = await db.execute("PRAGMA page_size")
                page_size = (await cursor.fetchone())[0]
                cursor = await db.execute("PRAGMA page_count")
                page_count = (await cursor.fetchone())[0]
                stats['database_size_bytes'] = page_size * page_count
                stats['database_size_mb'] = round((page_size * page_count) / (1024 * 1024), 2)
                
                # Performance stats
                stats['db_operations'] = self.db_operations
                stats['cache_hits'] = self.cache_hits
                stats['cache_misses'] = self.cache_misses
                stats['cache_hit_rate'] = round(
                    (self.cache_hits / (self.cache_hits + self.cache_misses) * 100) 
                    if (self.cache_hits + self.cache_misses) > 0 else 0, 2
                )
                
                return stats
        except Exception as e:
            print(f"❌ Failed to get database stats: {e}")
            return {}
    
    async def optimize_database(self):
        """Optimize database performance"""
        try:
            async with self.get_connection() as db:
                print("🔧 Optimizing database...")
                
                # Vacuum to reclaim space
                await db.execute("VACUUM")
                
                # Analyze for query optimization
                await db.execute("ANALYZE")
                
                # Clean up old metrics (keep last 7 days)
                week_ago = datetime.now() - timedelta(days=7)
                cursor = await db.execute("""
                    DELETE FROM bot_metrics WHERE timestamp < ?
                """, (week_ago,))
                metrics_cleaned = cursor.rowcount
                
                # Clean up old error logs (keep last 30 days)
                month_ago = datetime.now() - timedelta(days=30)
                cursor = await db.execute("""
                    DELETE FROM error_logs WHERE timestamp < ?
                """, (month_ago,))
                errors_cleaned = cursor.rowcount
                
                await db.commit()
                
                print(f"✅ Database optimized: {metrics_cleaned} old metrics, {errors_cleaned} old errors removed")
                return True
        except Exception as e:
            print(f"❌ Failed to optimize database: {e}")
            return False
    
    async def backup_database(self, backup_path: str = None) -> bool:
        """Create database backup"""
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"data/backups/bot_database_backup_{timestamp}.db"
            
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            async with self.get_connection() as source_db:
                # Use SQLite backup API
                backup_conn = await aiosqlite.connect(backup_file)
                await source_db.backup(backup_conn)
                await backup_conn.close()
            
            print(f"💾 Database backup created: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to create database backup: {e}")
            return False

# Global database manager instance
database_manager = DatabaseManager()