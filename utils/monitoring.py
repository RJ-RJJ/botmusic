"""
Comprehensive Monitoring System for Discord Music Bot
Tracks performance metrics, memory usage, cache efficiency, and voice latency
"""
import asyncio
import time
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
from utils.memory_manager import memory_manager
from utils.cache_manager import cache_manager
from utils.database_manager import database_manager

class PerformanceMonitor:
    """Advanced performance monitoring for the music bot"""
    
    def __init__(self):
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.current_stats = {}
        self.start_time = time.time()
        
        # FFmpeg process tracking
        self.ffmpeg_processes = set()
        
        # Voice latency tracking
        self.voice_latency_data = defaultdict(list)
        
        # Cache performance tracking
        self.cache_performance = {
            'hit_rates': deque(maxlen=100),
            'miss_rates': deque(maxlen=100),
            'eviction_counts': deque(maxlen=100)
        }

    async def record_metric(self, metric_type: str, value: float, guild_id: int = None, 
                          metadata: Dict[str, Any] = None):
        """Record a performance metric"""
        timestamp = time.time()
        
        metric_data = {
            'timestamp': timestamp,
            'value': value,
            'guild_id': guild_id,
            'metadata': metadata or {}
        }
        
        self.metrics_history[metric_type].append(metric_data)
        
        # Also store in database for persistence
        await database_manager.record_metric(metric_type, value, guild_id, metadata)

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        try:
            # Get memory manager stats
            memory_stats = memory_manager.get_stats()
            
            # Get system memory info
            system_memory = psutil.virtual_memory()
            
            # Calculate per-guild memory usage
            guild_memory = {}
            for category, objects in memory_stats.get('objects_by_category', {}).items():
                if 'guild' in category.lower():
                    guild_memory[category] = len(objects)
            
            return {
                'total_memory_mb': system_memory.total / (1024 * 1024),
                'available_memory_mb': system_memory.available / (1024 * 1024),
                'memory_usage_percent': system_memory.percent,
                'bot_memory_mb': memory_stats.get('total_tracked_memory', 0) / (1024 * 1024),
                'guild_memory_usage': guild_memory,
                'cache_memory_mb': await self._get_cache_memory_usage(),
                'tracked_objects': memory_stats.get('total_tracked_objects', 0)
            }
        except Exception as e:
            return {'error': str(e)}

    async def _get_cache_memory_usage(self) -> float:
        """Get cache memory usage in MB"""
        try:
            cache_stats = cache_manager.get_comprehensive_stats()
            total_entries = (
                cache_stats.get('metadata_cache', {}).get('size', 0) +
                cache_stats.get('stream_cache', {}).get('size', 0) +
                cache_stats.get('playlist_cache', {}).get('size', 0) +
                cache_stats.get('search_cache', {}).get('size', 0)
            )
            
            # Rough estimate: 2KB per entry average
            return (total_entries * 2048) / (1024 * 1024)
        except:
            return 0.0

    async def get_ffmpeg_stats(self) -> Dict[str, Any]:
        """Get FFmpeg process statistics"""
        try:
            # Count active FFmpeg processes
            ffmpeg_count = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'ffmpeg' in proc.info['name'].lower():
                        ffmpeg_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            return {
                'active_ffmpeg_processes': ffmpeg_count,
                'max_ffmpeg_processes': 20,  # Configurable limit
                'ffmpeg_utilization': (ffmpeg_count / 20) * 100 if 20 > 0 else 0
            }
        except Exception as e:
            return {'error': str(e)}

    async def get_cache_performance(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        try:
            cache_stats = cache_manager.get_comprehensive_stats()
            efficiency = cache_manager.get_cache_efficiency_report()
            
            return {
                'overall_hit_rate': efficiency.get('overall_hit_rate', 0),
                'total_hits': efficiency.get('total_hits', 0),
                'total_requests': efficiency.get('total_requests', 0),
                'cache_saves': cache_stats.get('cache_saves', 0),
                'cache_loads': cache_stats.get('cache_loads', 0),
                'metadata_cache': cache_stats.get('metadata_cache', {}),
                'stream_cache': cache_stats.get('stream_cache', {}),
                'playlist_cache': cache_stats.get('playlist_cache', {}),
                'search_cache': cache_stats.get('search_cache', {})
            }
        except Exception as e:
            return {'error': str(e)}

    async def get_voice_latency(self, guild_id: int = None) -> Dict[str, Any]:
        """Get voice connection latency data"""
        try:
            latency_data = {
                'average_latency_ms': 0,
                'max_latency_ms': 0,
                'min_latency_ms': 0,
                'packet_loss_percent': 0,
                'jitter_ms': 0
            }
            
            # This would integrate with actual voice client data
            # For now, return placeholder structure
            return latency_data
        except Exception as e:
            return {'error': str(e)}

    async def get_system_performance(self) -> Dict[str, Any]:
        """Get overall system performance metrics"""
        try:
            # Get system CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Get system memory
            memory = psutil.virtual_memory()
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            
            # Calculate bot uptime
            uptime_seconds = time.time() - self.start_time
            uptime_hours = uptime_seconds / 3600
            
            return {
                'cpu_usage_percent': cpu_percent,
                'memory_usage_percent': memory.percent,
                'disk_usage_percent': disk.percent,
                'uptime_hours': round(uptime_hours, 2),
                'uptime_formatted': str(timedelta(seconds=int(uptime_seconds))),
                'database_stats': await database_manager.get_database_stats()
            }
        except Exception as e:
            return {'error': str(e)}

    async def get_comprehensive_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        try:
            return {
                'timestamp': datetime.now().isoformat(),
                'memory_stats': await self.get_memory_stats(),
                'ffmpeg_stats': await self.get_ffmpeg_stats(),
                'cache_performance': await self.get_cache_performance(),
                'system_performance': await self.get_system_performance(),
                'uptime_hours': round((time.time() - self.start_time) / 3600, 2)
            }
        except Exception as e:
            return {'error': str(e)}

    async def start_periodic_monitoring(self):
        """Start periodic monitoring and reporting"""
        while True:
            try:
                # Generate comprehensive report every 5 minutes
                report = await self.get_comprehensive_report()
                
                # Store in database
                await database_manager.record_metric('performance_report', 1, 
                                                   metadata={'report': report})
                
                # Log key metrics
                print(f"📊 Performance Report - Uptime: {report.get('uptime_hours', 0)}h, "
                      f"Cache Hit Rate: {report.get('cache_performance', {}).get('overall_hit_rate', 0)}%")
                
                await asyncio.sleep(300)  # Every 5 minutes
                
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute

    def get_metric_summary(self, metric_type: str, hours: int = 24) -> Dict[str, Any]:
        """Get summary of specific metric over time period"""
        try:
            recent_data = []
            cutoff_time = time.time() - (hours * 3600)
            
            for metric in self.metrics_history[metric_type]:
                if metric['timestamp'] > cutoff_time:
                    recent_data.append(metric)
            
            if not recent_data:
                return {'count': 0, 'average': 0, 'min': 0, 'max': 0}
            
            values = [m['value'] for m in recent_data]
            return {
                'count': len(values),
                'average': sum(values) / len(values),
                'min': min(values),
                'max': max(values),
                'last_value': values[-1] if values else 0
            }
        except Exception:
            return {'count': 0, 'average': 0, 'min': 0, 'max': 0}

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Convenience functions for common monitoring tasks
async def record_memory_usage(guild_id: int = None):
    """Record current memory usage"""
    memory_stats = await performance_monitor.get_memory_stats()
    await performance_monitor.record_metric('memory_usage', 
                                          memory_stats.get('bot_memory_mb', 0), 
                                          guild_id)

async def record_ffmpeg_count():
    """Record current FFmpeg process count"""
    ffmpeg_stats = await performance_monitor.get_ffmpeg_stats()
    await performance_monitor.record_metric('ffmpeg_processes', 
                                          ffmpeg_stats.get('active_ffmpeg_processes', 0))

async def record_cache_hit_rate():
    """Record cache hit rate"""
    cache_stats = await performance_monitor.get_cache_performance()
    await performance_monitor.record_metric('cache_hit_rate', 
                                          cache_stats.get('overall_hit_rate', 0))

async def record_voice_latency(guild_id: int, latency_ms: float):
    """Record voice connection latency"""
    await performance_monitor.record_metric('voice_latency', latency_ms, guild_id)
