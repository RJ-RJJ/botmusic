"""
Helper functions for Discord Music Bot
Contains utility functions that don't belong to specific classes
"""
import discord
import asyncio

# Global bot instance reference (will be set by main bot)
_bot_instance = None

def set_bot_instance(bot):
    """Set the bot instance for helper functions"""
    global _bot_instance
    _bot_instance = bot

def get_server_count():
    """Get current server count"""
    if _bot_instance:
        return len(_bot_instance.guilds)
    return 0

def get_simple_status_messages():
    """Get simple 3-status rotation"""
    server_count = get_server_count()
    
    return [
        "?help",  # Listening to ?help
        f"{server_count} servers",  # Watching X servers
        "This bot is under development"  # Playing: This bot is under development
    ]

async def update_bot_status():
    """Simple 3-status rotation every 60 seconds"""
    if not _bot_instance:
        return
        
    await _bot_instance.wait_until_ready()
    
    status_messages = get_simple_status_messages()
    activity_types = [
        discord.ActivityType.listening,  # Listening to ?help
        discord.ActivityType.watching,   # Watching X servers  
        discord.ActivityType.playing     # Playing: This bot is under development
    ]
    
    current_index = 0
    
    while not _bot_instance.is_closed():
        try:
            # Always rotate through simple status messages (no song names)
            status_messages = get_simple_status_messages()  # Refresh server count
            status_text = status_messages[current_index % len(status_messages)]
            activity_type = activity_types[current_index % len(activity_types)]
            current_index += 1
            
            # Update bot presence
            activity = discord.Activity(type=activity_type, name=status_text)
            await _bot_instance.change_presence(activity=activity)
            
            # Wait 60 seconds before next update
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"Error updating bot status: {e}")
            await asyncio.sleep(60)  # Wait same time on error

async def on_voice_state_update_handler(member, before, after):
    """Handle auto-disconnect when bot is alone in voice channel"""
    if not _bot_instance or member.bot:
        return  # Ignore bot voice state changes
    
    # Get the Music cog
    music_cog = _bot_instance.get_cog('Music')
    if not music_cog:
        return
    
    # Check all guilds where the bot has voice states
    for guild_id, voice_state in music_cog.voice_states.items():
        if voice_state.voice and voice_state.voice.channel:
            # Count non-bot members in the voice channel
            non_bot_members = [m for m in voice_state.voice.channel.members if not m.bot]
            
            if len(non_bot_members) == 0:
                # Bot is alone, start disconnect timer
                voice_state.start_disconnect_timer()
            else:
                # Users present, cancel disconnect timer
                voice_state.cancel_disconnect_timer()