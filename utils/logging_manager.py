"""
Advanced Logging & Monitoring Manager for Discord Music Bot
Comprehensive logging, monitoring, and health check system
"""
import logging
import asyncio
import json
import time
import psutil
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from logging.handlers import RotatingFileHandler
from collections import deque, defaultdict
import weakref

class PerformanceTracker:
    """Track performance metrics and statistics"""
    
    def __init__(self):
        self.command_times = deque(maxlen=1000)  # Last 1000 command executions
        self.api_call_times = deque(maxlen=500)   # Last 500 API calls
        self.error_counts = defaultdict(int)
        self.connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'failed_connections': 0,
            'reconnections': 0
        }
        self.start_time = time.time()
        
        # Performance thresholds
        self.slow_command_threshold = 5.0  # seconds
        self.slow_api_threshold = 10.0     # seconds
        
    def track_command_execution(self, command_name: str, execution_time: float, success: bool):
        """Track command execution performance"""
        self.command_times.append({
            'command': command_name,
            'time': execution_time,
            'timestamp': time.time(),
            'success': success
        })
        
        if execution_time > self.slow_command_threshold:
            logging.warning(f"Slow command detected: {command_name} took {execution_time:.2f}s")
    
    def track_api_call(self, api_type: str, execution_time: float, success: bool):
        """Track API call performance"""
        self.api_call_times.append({
            'api': api_type,
            'time': execution_time,
            'timestamp': time.time(),
            'success': success
        })
        
        if execution_time > self.slow_api_threshold:
            logging.warning(f"Slow API call detected: {api_type} took {execution_time:.2f}s")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics"""
        now = time.time()
        uptime = now - self.start_time
        
        # Command statistics
        recent_commands = [cmd for cmd in self.command_times if now - cmd['timestamp'] < 3600]  # Last hour
        avg_command_time = sum(cmd['time'] for cmd in recent_commands) / len(recent_commands) if recent_commands else 0
        
        # API statistics
        recent_apis = [api for api in self.api_call_times if now - api['timestamp'] < 3600]  # Last hour
        avg_api_time = sum(api['time'] for api in recent_apis) / len(recent_apis) if recent_apis else 0
        
        return {
            'uptime_seconds': uptime,
            'uptime_formatted': str(timedelta(seconds=int(uptime))),
            'commands_executed': len(self.command_times),
            'api_calls_made': len(self.api_call_times),
            'avg_command_time': round(avg_command_time, 3),
            'avg_api_time': round(avg_api_time, 3),
            'recent_commands_per_hour': len(recent_commands),
            'recent_apis_per_hour': len(recent_apis),
            'connection_stats': self.connection_stats.copy()
        }

class LoggingManager:
    """Comprehensive logging and monitoring manager"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Performance tracker
        self.performance = PerformanceTracker()
        
        # Health monitoring
        self.health_checks = {}
        self.health_status = "healthy"
        self.last_health_check = None
        
        # Log retention settings
        self.log_retention_days = 30
        self.max_log_size_mb = 50
        
        # Setup loggers
        self._setup_loggers()
        
        # Alert thresholds
        self.alert_thresholds = {
            'memory_usage_percent': 85,
            'cpu_usage_percent': 80,
            'error_rate_per_minute': 10,
            'response_time_seconds': 15
        }
        
        # Alert history
        self.alerts_sent = deque(maxlen=100)
        
        # Monitoring data
        self.monitoring_data = {
            'memory_usage': deque(maxlen=720),    # 12 hours (1 point per minute)
            'cpu_usage': deque(maxlen=720),       # 12 hours
            'error_rates': deque(maxlen=720),     # 12 hours
            'response_times': deque(maxlen=720)   # 12 hours
        }
        
        self._monitoring_task = None
        
    def _setup_loggers(self):
        """Setup comprehensive logging system"""
        
        # Main bot logger
        self.bot_logger = logging.getLogger('bot')
        self.bot_logger.setLevel(logging.INFO)
        
        # Music logger
        self.music_logger = logging.getLogger('music')
        self.music_logger.setLevel(logging.INFO)
        
        # Error logger
        self.error_logger = logging.getLogger('errors')
        self.error_logger.setLevel(logging.ERROR)
        
        # Performance logger
        self.performance_logger = logging.getLogger('performance')
        self.performance_logger.setLevel(logging.INFO)
        
        # Database logger
        self.database_logger = logging.getLogger('database')
        self.database_logger.setLevel(logging.INFO)
        
        # Cache logger
        self.cache_logger = logging.getLogger('cache')
        self.cache_logger.setLevel(logging.INFO)
        
        # Setup file handlers
        self._setup_file_handlers()
        
        # Setup console handler
        self._setup_console_handler()
        
        logging.info("🔧 Logging system initialized")
        
    def _setup_file_handlers(self):
        """Setup rotating file handlers for different log types"""
        
        # Formatter
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Bot general logs
        bot_handler = RotatingFileHandler(
            self.log_dir / 'bot.log',
            maxBytes=self.max_log_size_mb * 1024 * 1024,
            backupCount=5
        )
        bot_handler.setFormatter(detailed_formatter)
        self.bot_logger.addHandler(bot_handler)
        
        # Music-specific logs
        music_handler = RotatingFileHandler(
            self.log_dir / 'music.log',
            maxBytes=self.max_log_size_mb * 1024 * 1024,
            backupCount=3
        )
        music_handler.setFormatter(detailed_formatter)
        self.music_logger.addHandler(music_handler)
        
        # Error logs
        error_handler = RotatingFileHandler(
            self.log_dir / 'errors.log',
            maxBytes=self.max_log_size_mb * 1024 * 1024,
            backupCount=10
        )
        error_handler.setFormatter(detailed_formatter)
        self.error_logger.addHandler(error_handler)
        
        # Performance logs
        performance_handler = RotatingFileHandler(
            self.log_dir / 'performance.log',
            maxBytes=self.max_log_size_mb * 1024 * 1024,
            backupCount=5
        )
        performance_handler.setFormatter(detailed_formatter)
        self.performance_logger.addHandler(performance_handler)
        
        # Database logs
        database_handler = RotatingFileHandler(
            self.log_dir / 'database.log',
            maxBytes=self.max_log_size_mb * 1024 * 1024,
            backupCount=3
        )
        database_handler.setFormatter(detailed_formatter)
        self.database_logger.addHandler(database_handler)
        
        # Cache logs
        cache_handler = RotatingFileHandler(
            self.log_dir / 'cache.log',
            maxBytes=self.max_log_size_mb * 1024 * 1024,
            backupCount=3
        )
        cache_handler.setFormatter(detailed_formatter)
        self.cache_logger.addHandler(cache_handler)
        
    def _setup_console_handler(self):
        """Setup console logging for important messages"""
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
        
        # Add to root logger
        logging.getLogger().addHandler(console_handler)
        logging.getLogger().setLevel(logging.INFO)
    
    def log_command_execution(self, command_name: str, user_id: int, guild_id: int, 
                            execution_time: float, success: bool, error: str = None):
        """Log command execution with performance tracking"""
        
        # Track performance
        self.performance.track_command_execution(command_name, execution_time, success)
        
        # Log to file
        if success:
            self.bot_logger.info(
                f"Command executed: {command_name} | User: {user_id} | Guild: {guild_id} | Time: {execution_time:.3f}s"
            )
        else:
            self.bot_logger.error(
                f"Command failed: {command_name} | User: {user_id} | Guild: {guild_id} | Time: {execution_time:.3f}s | Error: {error}"
            )
    
    def log_music_event(self, event_type: str, guild_id: int, details: Dict[str, Any]):
        """Log music-related events"""
        self.music_logger.info(
            f"{event_type} | Guild: {guild_id} | Details: {json.dumps(details)}"
        )
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log errors with full context and stack trace"""
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        }
        
        # Track error for performance monitoring
        self.performance.error_counts[error_info['error_type']] += 1
        
        # Log with stack trace
        self.error_logger.error(
            f"Error occurred: {json.dumps(error_info)}\n{traceback.format_exc()}"
        )
    
    def log_performance_metric(self, metric_name: str, value: float, context: Dict[str, Any] = None):
        """Log performance metrics"""
        metric_info = {
            'metric': metric_name,
            'value': value,
            'timestamp': time.time(),
            'context': context or {}
        }
        
        self.performance_logger.info(json.dumps(metric_info))
    
    def log_database_operation(self, operation: str, table: str, execution_time: float, success: bool):
        """Log database operations"""
        if success:
            self.database_logger.info(
                f"DB Operation: {operation} on {table} | Time: {execution_time:.3f}s"
            )
        else:
            self.database_logger.error(
                f"DB Operation Failed: {operation} on {table} | Time: {execution_time:.3f}s"
            )
    
    def log_cache_operation(self, operation: str, cache_type: str, hit: bool = None, details: str = ""):
        """Log cache operations"""
        hit_info = f" | Hit: {hit}" if hit is not None else ""
        details_info = f" | {details}" if details else ""
        
        self.cache_logger.info(
            f"Cache {operation}: {cache_type}{hit_info}{details_info}"
        )
    
    async def start_monitoring(self, interval: int = 60):
        """Start background monitoring of system health"""
        if self._monitoring_task and not self._monitoring_task.done():
            return
        
        self._monitoring_task = asyncio.create_task(self._monitoring_loop(interval))
        logging.info(f"📊 Health monitoring started (every {interval}s)")
    
    async def _monitoring_loop(self, interval: int):
        """Main monitoring loop"""
        while True:
            try:
                await asyncio.sleep(interval)
                await self._collect_system_metrics()
                await self._check_health()
                await self._cleanup_old_logs()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Monitoring loop error: {e}")
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            self.monitoring_data['memory_usage'].append({
                'timestamp': time.time(),
                'percent': memory.percent,
                'used_mb': memory.used // (1024 * 1024),
                'available_mb': memory.available // (1024 * 1024)
            })
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.monitoring_data['cpu_usage'].append({
                'timestamp': time.time(),
                'percent': cpu_percent
            })
            
            # Calculate error rate (errors per minute)
            now = time.time()
            recent_errors = sum(
                1 for cmd in self.performance.command_times 
                if now - cmd['timestamp'] < 60 and not cmd['success']
            )
            self.monitoring_data['error_rates'].append({
                'timestamp': now,
                'errors_per_minute': recent_errors
            })
            
            # Calculate average response time
            recent_commands = [
                cmd for cmd in self.performance.command_times 
                if now - cmd['timestamp'] < 60
            ]
            avg_response = sum(cmd['time'] for cmd in recent_commands) / len(recent_commands) if recent_commands else 0
            self.monitoring_data['response_times'].append({
                'timestamp': now,
                'avg_response_time': avg_response
            })
            
            # Check for alerts
            await self._check_alerts(memory.percent, cpu_percent, recent_errors, avg_response)
            
        except Exception as e:
            logging.error(f"Failed to collect system metrics: {e}")
    
    async def _check_alerts(self, memory_percent: float, cpu_percent: float, 
                          error_rate: int, response_time: float):
        """Check if any metrics exceed alert thresholds"""
        alerts = []
        
        if memory_percent > self.alert_thresholds['memory_usage_percent']:
            alerts.append(f"High memory usage: {memory_percent:.1f}%")
        
        if cpu_percent > self.alert_thresholds['cpu_usage_percent']:
            alerts.append(f"High CPU usage: {cpu_percent:.1f}%")
        
        if error_rate > self.alert_thresholds['error_rate_per_minute']:
            alerts.append(f"High error rate: {error_rate} errors/minute")
        
        if response_time > self.alert_thresholds['response_time_seconds']:
            alerts.append(f"Slow response time: {response_time:.2f}s")
        
        # Log alerts
        for alert in alerts:
            logging.warning(f"🚨 ALERT: {alert}")
            self.alerts_sent.append({
                'timestamp': time.time(),
                'alert': alert,
                'severity': 'high' if 'High' in alert else 'medium'
            })
    
    async def _check_health(self):
        """Perform comprehensive health checks"""
        health_issues = []
        
        try:
            # Check system resources
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                health_issues.append("Critical memory usage")
            
            # Check disk space
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                health_issues.append("Critical disk usage")
            
            # Check if we have too many errors
            error_count = sum(self.performance.error_counts.values())
            if error_count > 50:  # More than 50 errors since startup
                health_issues.append("High error count")
            
            # Update health status
            if health_issues:
                self.health_status = "unhealthy"
                logging.warning(f"Health check failed: {', '.join(health_issues)}")
            else:
                self.health_status = "healthy"
            
            self.last_health_check = time.time()
            
        except Exception as e:
            logging.error(f"Health check failed: {e}")
            self.health_status = "unknown"
    
    async def _cleanup_old_logs(self):
        """Clean up old log files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.log_retention_days)
            
            for log_file in self.log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    logging.info(f"Cleaned up old log file: {log_file.name}")
                    
        except Exception as e:
            logging.error(f"Failed to cleanup old logs: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return {
            'status': self.health_status,
            'last_check': self.last_health_check,
            'last_check_formatted': datetime.fromtimestamp(self.last_health_check).strftime('%Y-%m-%d %H:%M:%S') if self.last_health_check else 'Never',
            'uptime': time.time() - self.performance.start_time,
            'recent_alerts': list(self.alerts_sent)[-5:] if self.alerts_sent else []
        }
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get comprehensive monitoring summary"""
        # Get latest metrics
        latest_memory = self.monitoring_data['memory_usage'][-1] if self.monitoring_data['memory_usage'] else {}
        latest_cpu = self.monitoring_data['cpu_usage'][-1] if self.monitoring_data['cpu_usage'] else {}
        latest_errors = self.monitoring_data['error_rates'][-1] if self.monitoring_data['error_rates'] else {}
        latest_response = self.monitoring_data['response_times'][-1] if self.monitoring_data['response_times'] else {}
        
        return {
            'health_status': self.get_health_status(),
            'performance_summary': self.performance.get_performance_summary(),
            'current_metrics': {
                'memory_percent': latest_memory.get('percent', 0),
                'memory_used_mb': latest_memory.get('used_mb', 0),
                'cpu_percent': latest_cpu.get('percent', 0),
                'errors_per_minute': latest_errors.get('errors_per_minute', 0),
                'avg_response_time': latest_response.get('avg_response_time', 0)
            },
            'alert_thresholds': self.alert_thresholds,
            'total_alerts': len(self.alerts_sent),
            'log_files': [f.name for f in self.log_dir.glob("*.log")]
        }
    
    def get_log_files_info(self) -> List[Dict[str, Any]]:
        """Get information about log files"""
        log_files = []
        
        for log_file in self.log_dir.glob("*.log*"):
            stat = log_file.stat()
            log_files.append({
                'name': log_file.name,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'lines': self._count_lines(log_file) if log_file.suffix == '.log' else 'N/A'
            })
        
        return sorted(log_files, key=lambda x: x['name'])
    
    def _count_lines(self, file_path: Path) -> int:
        """Count lines in a file efficiently"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except:
            return 0
    
    def export_logs(self, log_type: str = "all", hours: int = 24) -> Optional[str]:
        """Export logs for the specified time period"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            if log_type == "all":
                log_files = list(self.log_dir.glob("*.log"))
            else:
                log_files = [self.log_dir / f"{log_type}.log"]
            
            export_data = []
            
            for log_file in log_files:
                if not log_file.exists():
                    continue
                
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        try:
                            # Parse timestamp from log line
                            timestamp_str = line.split(' | ')[0]
                            log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            
                            if log_time >= cutoff_time:
                                export_data.append({
                                    'file': log_file.name,
                                    'timestamp': timestamp_str,
                                    'content': line.strip()
                                })
                        except:
                            continue
            
            # Sort by timestamp
            export_data.sort(key=lambda x: x['timestamp'])
            
            # Create export file
            export_file = self.log_dir / f"export_{log_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            
            return str(export_file)
            
        except Exception as e:
            logging.error(f"Failed to export logs: {e}")
            return None

# Global logging manager instance
logging_manager = LoggingManager()