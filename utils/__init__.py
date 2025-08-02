"""
Utils package for Discord Music Bot
Contains utility classes and helper functions
"""

from .exceptions import VoiceError, YTDLError
from .song import Song
from .song_queue import SongQueue
from .ytdl_source import YTDLSource
from .voice_state import VoiceState
from .helpers import (
    set_bot_instance, 
    get_server_count, 
    get_simple_status_messages, 
    update_bot_status,
    on_voice_state_update_handler
)
from .memory_manager import memory_manager
from .error_handler import error_handler
from .cache_manager import cache_manager
from .database_manager import database_manager
from .logging_manager import logging_manager
from .health_monitor import health_monitor, initialize_health_monitor
from .ui_enhancements import (
    ProgressBar, LoadingIndicator, EnhancedEmbed, 
    InteractionEnhancer, SmartPlaybackFeedback,
    format_duration, format_file_size, format_time_ago, truncate_text
)

__all__ = [
    'VoiceError',
    'YTDLError', 
    'Song',
    'SongQueue',
    'YTDLSource',
    'VoiceState',
    'set_bot_instance',
    'get_server_count',
    'get_simple_status_messages',
    'update_bot_status',
    'on_voice_state_update_handler',
    'memory_manager',
    'error_handler',
    'cache_manager',
    'database_manager',
    'logging_manager',
    'health_monitor',
    'initialize_health_monitor',
    'ProgressBar',
    'LoadingIndicator',
    'EnhancedEmbed',
    'InteractionEnhancer',
    'SmartPlaybackFeedback',
    'format_duration',
    'format_file_size',
    'format_time_ago',
    'truncate_text'
]