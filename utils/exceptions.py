"""
Custom exceptions for Discord Music Bot
"""

class VoiceError(Exception):
    """Exception raised for voice-related errors"""
    pass

class YTDLError(Exception):
    """Exception raised for YTDL-related errors"""
    pass