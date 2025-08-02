"""
Discord Music Bot - Main Entry Point
A modern, modular Discord music bot with playlist support

Refactored version with better code organization and maintainability
"""
import discord
from discord.ext import commands
import asyncio

# Import configuration
from config import TOKEN, PREFIX, get_bot_intents

# Import utility functions
from utils import (
    set_bot_instance, 
    update_bot_status, 
    on_voice_state_update_handler
)
from utils.memory_manager import memory_manager
from utils.error_handler import error_handler
from utils.cache_manager import cache_manager

# Import cogs
from cogs import Music, Info

class MusicBot(commands.Bot):
    """Main bot class with enhanced functionality"""
    
    def __init__(self):
        # Initialize bot with proper intents
        intents = get_bot_intents()
        super().__init__(command_prefix=PREFIX, intents=intents)
        
        # Remove default help command to use our custom one
        self.remove_command('help')
        
        # Set up bot instance for helper functions
        set_bot_instance(self)
    
    async def setup_hook(self):
        """Called when the bot is starting up"""
        print("🔧 Setting up bot...")
        
        # Load cogs
        await self.add_cog(Music(self))
        await self.add_cog(Info(self))
        
        print("✅ All cogs loaded successfully")
    
    async def on_ready(self):
        """Called when bot is ready and connected"""
        print(f'✅ Bot ready! Logged in as {self.user}')
        print(f'🎵 Connected to {len(self.guilds)} servers')
        print(f'🎵 Using Python with yt-dlp')
        
        # Import FFMPEG_EXECUTABLE here to avoid circular imports
        from config.settings import FFMPEG_EXECUTABLE
        ffmpeg_type = "Local FFmpeg" if "ffmpeg.exe" in FFMPEG_EXECUTABLE else "System FFmpeg"
        print(f'🎵 FFmpeg: {ffmpeg_type} ({FFMPEG_EXECUTABLE})')
        print(f'🎧 Status: Simple 3-status rotation system started')
        
        # Start dynamic status updater
        self.loop.create_task(update_bot_status())
        
        # Start memory manager periodic cleanup (every 5 minutes)
        memory_manager.start_periodic_cleanup(self.loop, interval=300)
        print(f'🧠 Memory manager started with 5-minute cleanup cycle')
        
        # Initialize cache system
        await cache_manager.load_cache_from_disk()
        await cache_manager.start_background_cleanup(interval=600)  # 10 minutes
        print(f'⚡ Cache system initialized with background cleanup')
    
    async def on_command_error(self, ctx, error):
        """Global error handler using centralized error handling system"""
        # Use centralized error handler
        await error_handler.handle_error(error, ctx)
    
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates for auto-disconnect"""
        await on_voice_state_update_handler(member, before, after)

def main():
    """Main function to run the bot"""
    try:
        # Create and run the bot
        bot = MusicBot()
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Critical error: {e}")
        raise

if __name__ == '__main__':
    main()