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
    'on_voice_state_update_handler'
]