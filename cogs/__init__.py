"""
Cogs package for Discord Music Bot
Contains all Discord cogs (command groups)
"""

# Import cogs for easier access
from .music import Music
from .info import Info

__all__ = [
    'Music',
    'Info'
]