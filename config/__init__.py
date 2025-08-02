"""
Configuration package for Discord Music Bot
Contains bot configuration and settings
"""

from .settings import (
    PREFIX,
    TOKEN,
    FFMPEG_EXECUTABLE,
    FFMPEG_OPTIONS,
    YDL_OPTIONS,
    PLAYLIST_BATCH_SIZE,
    PLAYLIST_LOW_THRESHOLD,
    CONCURRENT_LOAD_LIMIT,
    AUTO_DISCONNECT_DELAY,
    get_ffmpeg_executable,
    get_bot_intents,
    get_server_count,
    get_simple_status_messages
)

__all__ = [
    'PREFIX',
    'TOKEN', 
    'FFMPEG_EXECUTABLE',
    'FFMPEG_OPTIONS',
    'YDL_OPTIONS',
    'PLAYLIST_BATCH_SIZE',
    'PLAYLIST_LOW_THRESHOLD',
    'CONCURRENT_LOAD_LIMIT',
    'AUTO_DISCONNECT_DELAY',
    'get_ffmpeg_executable',
    'get_bot_intents',
    'get_server_count',
    'get_simple_status_messages'
]