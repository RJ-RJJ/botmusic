"""
Advanced Health Monitor & Performance Metrics for Discord Music Bot
Comprehensive health checking, metrics collection, and performance analysis
"""
import asyncio
import time
import psutil
import discord
from discord.ext import commands
import yt_dlp
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from collections import deque, defaultdict
import json
import traceback
from pathlib import Path

class HealthCheck:
    """Individual health check definition"""
    
    def __init__(self, name: str, check_func: Callable, critical: bool = False, 
                 timeout: int = 30, interval: int = 300):
        self.name = name
        self.check_func = check_func
        self.critical = critical  # If True, bot is considered unhealthy if this fails
        self.timeout = timeout    # Max time for check to complete
        self.interval = interval  # How often to run this check (seconds)
        self.last_run = 0
        self.last_result = None
        self.last_duration = 0
        self.failure_count = 0
        self.total_runs = 0
        
    async def run(self) -> Dict[str, Any]:
        """Run the health check"""
        start_time = time.time()
        self.last_run = start_time
        self.total_runs += 1
        
        try:
            # Run check with timeout
            result = await asyncio.wait_for(self.check_func(), timeout=self.timeout)
            self.last_duration = time.time() - start_time
            
            if result.get('healthy', False):
                self.failure_count = 0
                self.last_result = result
                return {
                    'name': self.name,
                    'healthy': True,
                    'duration': self.last_duration,
                    'result': result,
                    'critical': self.critical
                }
            else:
                self.failure_count += 1
                self.last_result = result
                return {
                    'name': self.name,
                    'healthy': False,
                    'duration': self.last_duration,
                    'result': result,
                    'critical': self.critical,
                    'failure_count': self.failure_count
                }
                
        except asyncio.TimeoutError:
            self.failure_count += 1
            self.last_duration = time.time() - start_time
            error_result = {'healthy': False, 'error': f'Health check timed out after {self.timeout}s'}
            self.last_result = error_result
            return {
                'name': self.name,
                'healthy': False,
                'duration': self.last_duration,
                'result': error_result,
                'critical': self.critical,
                'failure_count': self.failure_count
            }
        except Exception as e:
            self.failure_count += 1
            self.last_duration = time.time() - start_time
            error_result = {'healthy': False, 'error': str(e)}
            self.last_result = error_result
            return {
                'name': self.name,
                'healthy': False,
                'duration': self.last_duration,
                'result': error_result,
                'critical': self.critical,
                'failure_count': self.failure_count
            }
    
    def should_run(self) -> bool:
        """Check if this health check should run now"""
        return time.time() - self.last_run >= self.interval

class PerformanceMetrics:
    """Advanced performance metrics collection"""
    
    def __init__(self):
        self.metrics = defaultdict(deque)
        self.max_history = 1440  # 24 hours of minute-by-minute data
        
        # Real-time counters
        self.counters = defaultdict(int)
        
        # Performance baselines
        self.baselines = {
            'memory_usage_mb': 100,      # Expected base memory
            'cpu_usage_percent': 5,      # Expected base CPU
            'command_response_ms': 500,   # Expected command response
            'api_response_ms': 2000      # Expected API response
        }
        
        # Alert conditions
        self.alert_conditions = {
            'high_memory': lambda x: x > 300,  # > 300MB
            'high_cpu': lambda x: x > 80,      # > 80%
            'slow_commands': lambda x: x > 5000,  # > 5 seconds
            'high_error_rate': lambda x: x > 0.1  # > 10% error rate
        }
        
    def record_metric(self, metric_name: str, value: float, timestamp: float = None):
        """Record a metric value"""
        if timestamp is None:
            timestamp = time.time()
            
        # Add to history
        self.metrics[metric_name].append({
            'value': value,
            'timestamp': timestamp
        })
        
        # Maintain max history
        while len(self.metrics[metric_name]) > self.max_history:
            self.metrics[metric_name].popleft()
    
    def increment_counter(self, counter_name: str, amount: int = 1):
        """Increment a counter"""
        self.counters[counter_name] += amount
    
    def get_metric_summary(self, metric_name: str, hours: int = 1) -> Dict[str, Any]:
        """Get summary statistics for a metric"""
        if metric_name not in self.metrics:
            return {'error': 'Metric not found'}
        
        cutoff_time = time.time() - (hours * 3600)
        recent_data = [
            point for point in self.metrics[metric_name] 
            if point['timestamp'] >= cutoff_time
        ]
        
        if not recent_data:
            return {'error': 'No recent data'}
        
        values = [point['value'] for point in recent_data]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'latest': values[-1],
            'trend': 'increasing' if len(values) > 1 and values[-1] > values[0] else 'stable/decreasing'
        }
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for alert conditions"""
        alerts = []
        
        # Check memory usage
        memory_summary = self.get_metric_summary('memory_usage_mb', hours=0.25)  # Last 15 minutes
        if 'avg' in memory_summary and self.alert_conditions['high_memory'](memory_summary['avg']):
            alerts.append({
                'type': 'high_memory',
                'severity': 'high',
                'message': f"High memory usage: {memory_summary['avg']:.1f} MB average",
                'value': memory_summary['avg']
            })
        
        # Check CPU usage
        cpu_summary = self.get_metric_summary('cpu_usage_percent', hours=0.25)
        if 'avg' in cpu_summary and self.alert_conditions['high_cpu'](cpu_summary['avg']):
            alerts.append({
                'type': 'high_cpu',
                'severity': 'high',
                'message': f"High CPU usage: {cpu_summary['avg']:.1f}% average",
                'value': cpu_summary['avg']
            })
        
        # Check command response times
        response_summary = self.get_metric_summary('command_response_ms', hours=0.25)
        if 'avg' in response_summary and self.alert_conditions['slow_commands'](response_summary['avg']):
            alerts.append({
                'type': 'slow_commands',
                'severity': 'medium',
                'message': f"Slow command responses: {response_summary['avg']:.0f}ms average",
                'value': response_summary['avg']
            })
        
        return alerts

class HealthMonitor:
    """Main health monitoring system"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.health_checks = {}
        self.performance = PerformanceMetrics()
        self.monitoring_task = None
        self.last_full_check = None
        
        # Overall health status
        self.overall_status = "unknown"
        self.status_message = "Health monitoring not started"
        
        # Health history
        self.health_history = deque(maxlen=288)  # 24 hours of 5-minute checks
        
        # Setup default health checks
        self._setup_default_checks()
        
    def _setup_default_checks(self):
        """Setup default health checks"""
        
        # System resource checks
        self.add_health_check(
            "system_resources",
            self._check_system_resources,
            critical=True,
            interval=60
        )
        
        # Discord connection check
        self.add_health_check(
            "discord_connection",
            self._check_discord_connection,
            critical=True,
            interval=120
        )
        
        # Database connectivity
        self.add_health_check(
            "database_health",
            self._check_database_health,
            critical=False,
            interval=300
        )
        
        # Cache system health
        self.add_health_check(
            "cache_health",
            self._check_cache_health,
            critical=False,
            interval=300
        )
        
        # YTDL functionality
        self.add_health_check(
            "ytdl_functionality",
            self._check_ytdl_functionality,
            critical=False,
            interval=600
        )
        
        # Voice system health
        self.add_health_check(
            "voice_system",
            self._check_voice_system,
            critical=False,
            interval=180
        )
    
    def add_health_check(self, name: str, check_func: Callable, 
                        critical: bool = False, timeout: int = 30, interval: int = 300):
        """Add a custom health check"""
        self.health_checks[name] = HealthCheck(name, check_func, critical, timeout, interval)
    
    async def start_monitoring(self, interval: int = 60):
        """Start the health monitoring system"""
        if self.monitoring_task and not self.monitoring_task.done():
            return
        
        self.monitoring_task = asyncio.create_task(self._monitoring_loop(interval))
        print("🏥 Health monitoring system started")
    
    async def _monitoring_loop(self, interval: int):
        """Main monitoring loop"""
        while True:
            try:
                await asyncio.sleep(interval)
                
                # Collect system metrics
                await self._collect_metrics()
                
                # Run health checks
                await self._run_health_checks()
                
                # Check for alerts
                alerts = self.performance.check_alerts()
                if alerts:
                    await self._handle_alerts(alerts)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Health monitoring error: {e}")
                traceback.print_exc()
    
    async def _collect_metrics(self):
        """Collect system performance metrics"""
        timestamp = time.time()
        
        try:
            # System metrics
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Record metrics
            self.performance.record_metric('memory_usage_mb', memory.used / (1024 * 1024), timestamp)
            self.performance.record_metric('memory_percent', memory.percent, timestamp)
            self.performance.record_metric('cpu_usage_percent', cpu_percent, timestamp)
            
            # Discord-specific metrics
            if self.bot.is_ready():
                self.performance.record_metric('guild_count', len(self.bot.guilds), timestamp)
                
                # Count active voice connections
                active_voice = sum(1 for guild in self.bot.guilds if guild.voice_client)
                self.performance.record_metric('active_voice_connections', active_voice, timestamp)
                
            # Process metrics
            process = psutil.Process()
            self.performance.record_metric('process_memory_mb', process.memory_info().rss / (1024 * 1024), timestamp)
            self.performance.record_metric('open_files', len(process.open_files()), timestamp)
            self.performance.record_metric('thread_count', process.num_threads(), timestamp)
            
        except Exception as e:
            print(f"⚠️ Error collecting metrics: {e}")
    
    async def _run_health_checks(self):
        """Run all health checks that are due"""
        check_results = []
        
        for check in self.health_checks.values():
            if check.should_run():
                try:
                    result = await check.run()
                    check_results.append(result)
                except Exception as e:
                    print(f"⚠️ Health check {check.name} failed with exception: {e}")
        
        if check_results:
            await self._process_health_results(check_results)
    
    async def _process_health_results(self, results: List[Dict[str, Any]]):
        """Process health check results and update overall status"""
        critical_failures = [r for r in results if not r['healthy'] and r['critical']]
        total_failures = [r for r in results if not r['healthy']]
        
        # Determine overall health
        if critical_failures:
            self.overall_status = "critical"
            self.status_message = f"{len(critical_failures)} critical health check(s) failed"
        elif len(total_failures) > len(results) // 2:  # More than half failed
            self.overall_status = "unhealthy"
            self.status_message = f"{len(total_failures)} of {len(results)} health checks failed"
        elif total_failures:
            self.overall_status = "degraded"
            self.status_message = f"{len(total_failures)} non-critical health check(s) failed"
        else:
            self.overall_status = "healthy"
            self.status_message = f"All {len(results)} health checks passed"
        
        # Record in history
        self.health_history.append({
            'timestamp': time.time(),
            'status': self.overall_status,
            'checks_run': len(results),
            'failures': len(total_failures),
            'critical_failures': len(critical_failures)
        })
        
        self.last_full_check = time.time()
        
        # Log significant status changes
        if critical_failures or (len(total_failures) > 0 and self.overall_status != "degraded"):
            print(f"🏥 Health status: {self.overall_status.upper()} - {self.status_message}")
    
    async def _handle_alerts(self, alerts: List[Dict[str, Any]]):
        """Handle performance alerts"""
        for alert in alerts:
            print(f"🚨 PERFORMANCE ALERT [{alert['severity'].upper()}]: {alert['message']}")
            
            # You could extend this to send alerts to a Discord channel or webhook
            # await self._send_alert_to_channel(alert)
    
    # Health Check Functions
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            issues = []
            if memory.percent > 90:
                issues.append(f"Memory usage critical: {memory.percent:.1f}%")
            if disk.percent > 90:
                issues.append(f"Disk usage critical: {disk.percent:.1f}%")
            
            return {
                'healthy': len(issues) == 0,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'issues': issues
            }
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    async def _check_discord_connection(self) -> Dict[str, Any]:
        """Check Discord connection health"""
        try:
            if not self.bot.is_ready():
                return {'healthy': False, 'error': 'Bot is not ready'}
            
            if not self.bot.is_closed():
                latency = self.bot.latency * 1000  # Convert to ms
                
                if latency > 500:  # High latency
                    return {
                        'healthy': False,
                        'latency_ms': latency,
                        'error': f'High latency: {latency:.0f}ms'
                    }
                
                return {
                    'healthy': True,
                    'latency_ms': latency,
                    'guild_count': len(self.bot.guilds)
                }
            else:
                return {'healthy': False, 'error': 'Bot connection is closed'}
                
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            from utils.database_manager import database_manager
            
            start_time = time.time()
            
            # Simple database operation
            stats = await database_manager.get_database_stats()
            
            operation_time = (time.time() - start_time) * 1000  # ms
            
            if operation_time > 5000:  # > 5 seconds
                return {
                    'healthy': False,
                    'operation_time_ms': operation_time,
                    'error': 'Database operation too slow'
                }
            
            return {
                'healthy': True,
                'operation_time_ms': operation_time,
                'database_size_mb': stats.get('database_size_mb', 0)
            }
            
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    async def _check_cache_health(self) -> Dict[str, Any]:
        """Check cache system health"""
        try:
            from utils.cache_manager import cache_manager
            
            stats = cache_manager.get_comprehensive_stats()
            efficiency = cache_manager.get_cache_efficiency_report()
            
            hit_rate = efficiency.get('overall_hit_rate', 0)
            
            # Cache should have reasonable hit rate if it's been running
            if stats['total_entries'] > 100 and hit_rate < 20:
                return {
                    'healthy': False,
                    'hit_rate': hit_rate,
                    'total_entries': stats['total_entries'],
                    'error': 'Cache hit rate too low'
                }
            
            return {
                'healthy': True,
                'hit_rate': hit_rate,
                'total_entries': stats['total_entries'],
                'uptime': stats['uptime_formatted']
            }
            
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    async def _check_ytdl_functionality(self) -> Dict[str, Any]:
        """Check YTDL/yt-dlp functionality"""
        try:
            # Test with a simple, reliable video
            test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # Me at the zoo (first YouTube video)
            
            start_time = time.time()
            
            # Quick test extraction (metadata only)
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'skip_download': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(test_url, download=False)
            
            extraction_time = (time.time() - start_time) * 1000  # ms
            
            if extraction_time > 10000:  # > 10 seconds
                return {
                    'healthy': False,
                    'extraction_time_ms': extraction_time,
                    'error': 'YTDL extraction too slow'
                }
            
            return {
                'healthy': True,
                'extraction_time_ms': extraction_time,
                'title': info.get('title', 'Unknown')
            }
            
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    async def _check_voice_system(self) -> Dict[str, Any]:
        """Check voice system health"""
        try:
            active_connections = 0
            problematic_connections = 0
            
            for guild in self.bot.guilds:
                if guild.voice_client:
                    active_connections += 1
                    
                    # Check if voice client is in a problematic state
                    if not guild.voice_client.is_connected():
                        problematic_connections += 1
            
            return {
                'healthy': True,
                'active_connections': active_connections,
                'problematic_connections': problematic_connections,
                'total_guilds': len(self.bot.guilds)
            }
            
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    # Public interface methods
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return {
            'status': self.overall_status,
            'message': self.status_message,
            'last_check': self.last_full_check,
            'last_check_formatted': datetime.fromtimestamp(self.last_full_check).strftime('%Y-%m-%d %H:%M:%S') if self.last_full_check else 'Never',
            'checks_registered': len(self.health_checks),
            'monitoring_active': self.monitoring_task is not None and not self.monitoring_task.done()
        }
    
    def get_detailed_health_report(self) -> Dict[str, Any]:
        """Get detailed health report"""
        check_details = {}
        
        for name, check in self.health_checks.items():
            check_details[name] = {
                'last_result': check.last_result,
                'last_run': check.last_run,
                'last_duration': check.last_duration,
                'failure_count': check.failure_count,
                'total_runs': check.total_runs,
                'critical': check.critical,
                'success_rate': ((check.total_runs - check.failure_count) / check.total_runs * 100) if check.total_runs > 0 else 0
            }
        
        return {
            'overall_status': self.get_health_status(),
            'check_details': check_details,
            'recent_alerts': self.performance.check_alerts(),
            'health_history': list(self.health_history)[-10:]  # Last 10 health check results
        }
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data"""
        dashboard = {
            'health_status': self.get_health_status(),
            'system_metrics': {},
            'performance_trends': {},
            'alerts': self.performance.check_alerts(),
            'counters': dict(self.performance.counters)
        }
        
        # Get system metrics summaries
        metric_names = ['memory_usage_mb', 'cpu_usage_percent', 'guild_count', 'active_voice_connections']
        for metric in metric_names:
            dashboard['system_metrics'][metric] = self.performance.get_metric_summary(metric, hours=1)
        
        # Get performance trends (last 4 hours)
        trend_metrics = ['memory_percent', 'cpu_usage_percent', 'process_memory_mb']
        for metric in trend_metrics:
            dashboard['performance_trends'][metric] = self.performance.get_metric_summary(metric, hours=4)
        
        return dashboard

# Global health monitor instance (will be initialized with bot instance)
health_monitor: Optional[HealthMonitor] = None

def initialize_health_monitor(bot: commands.Bot):
    """Initialize the global health monitor"""
    global health_monitor
    health_monitor = HealthMonitor(bot)
    return health_monitor