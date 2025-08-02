"""
UI Enhancements & Progress Indicators for Discord Music Bot
Enhanced user experience with better progress feedback and interactions
"""
import discord
from discord.ext import commands
import asyncio
import time
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
import math

class ProgressBar:
    """Create visual progress bars for Discord embeds"""
    
    @staticmethod
    def create_bar(progress: float, length: int = 20, fill_char: str = "█", empty_char: str = "░") -> str:
        """Create a visual progress bar"""
        if progress < 0:
            progress = 0
        elif progress > 1:
            progress = 1
        
        filled_length = int(length * progress)
        empty_length = length - filled_length
        
        return f"`{fill_char * filled_length}{empty_char * empty_length}`"
    
    @staticmethod
    def create_volume_bar(volume: float, length: int = 20) -> str:
        """Create a volume-specific progress bar"""
        return ProgressBar.create_bar(volume, length, "█", "░")
    
    @staticmethod
    def create_time_bar(current: int, total: int, length: int = 25) -> str:
        """Create a time progress bar with timestamps"""
        if total <= 0:
            return f"`{'░' * length}` 🔴 LIVE"
        
        progress = current / total
        bar = ProgressBar.create_bar(progress, length)
        
        current_time = f"{current // 60}:{current % 60:02d}"
        total_time = f"{total // 60}:{total % 60:02d}"
        
        return f"{bar} `{current_time} / {total_time}`"

class LoadingIndicator:
    """Animated loading indicators for Discord messages"""
    
    def __init__(self, ctx: commands.Context, initial_message: str = "Loading..."):
        self.ctx = ctx
        self.message = None
        self.initial_message = initial_message
        self.is_active = False
        self.animation_task = None
        
        # Loading animations
        self.spinners = {
            'dots': ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
            'clock': ['🕐', '🕑', '🕒', '🕓', '🕔', '🕕', '🕖', '🕗', '🕘', '🕙', '🕚', '🕛'],
            'bounce': ['⠁', '⠂', '⠄', '⠂'],
            'music': ['🎵', '🎶', '🎵', '🎶']
        }
        
        # Progress stages
        self.stages = [
            "🔍 Searching for song...",
            "📡 Connecting to source...",
            "⬇️ Extracting audio info...",
            "🎵 Preparing playback...",
            "✅ Ready to play!"
        ]
        
    async def start(self, animation_type: str = 'music', update_interval: float = 0.5):
        """Start the loading animation"""
        if self.is_active:
            return
        
        self.is_active = True
        
        # Send initial message
        embed = discord.Embed(
            title="🎵 Music Bot",
            description=f"{self.spinners[animation_type][0]} {self.initial_message}",
            color=discord.Color.blue()
        )
        
        self.message = await self.ctx.send(embed=embed)
        
        # Start animation task
        self.animation_task = asyncio.create_task(
            self._animate(animation_type, update_interval)
        )
    
    async def _animate(self, animation_type: str, update_interval: float):
        """Run the loading animation"""
        spinner = self.spinners[animation_type]
        frame = 0
        
        while self.is_active:
            try:
                current_spinner = spinner[frame % len(spinner)]
                
                embed = discord.Embed(
                    title="🎵 Music Bot",
                    description=f"{current_spinner} {self.initial_message}",
                    color=discord.Color.blue()
                )
                
                await self.message.edit(embed=embed)
                frame += 1
                
                await asyncio.sleep(update_interval)
                
            except discord.NotFound:
                # Message was deleted
                break
            except Exception as e:
                print(f"Animation error: {e}")
                break
    
    async def update_message(self, new_message: str):
        """Update the loading message"""
        self.initial_message = new_message
    
    async def update_stage(self, stage_index: int):
        """Update to a specific stage"""
        if 0 <= stage_index < len(self.stages):
            await self.update_message(self.stages[stage_index])
    
    async def stop(self, final_message: str = None, final_color: discord.Color = discord.Color.green()):
        """Stop the loading animation"""
        self.is_active = False
        
        if self.animation_task:
            self.animation_task.cancel()
        
        if self.message and final_message:
            embed = discord.Embed(
                title="🎵 Music Bot",
                description=final_message,
                color=final_color
            )
            
            try:
                await self.message.edit(embed=embed)
            except discord.NotFound:
                pass

class EnhancedEmbed:
    """Enhanced embed creation with better formatting"""
    
    @staticmethod
    def create_music_embed(title: str, description: str = None, color: discord.Color = discord.Color.blue()) -> discord.Embed:
        """Create a music-themed embed"""
        embed = discord.Embed(title=f"🎵 {title}", description=description, color=color)
        embed.set_footer(text="🎧 Discord Music Bot", icon_url="https://cdn.discordapp.com/emojis/741605543046807626.png")
        return embed
    
    @staticmethod
    def create_now_playing_embed(song_info: Dict[str, Any], voice_state: Any = None) -> discord.Embed:
        """Create an enhanced now playing embed"""
        title = song_info.get('title', 'Unknown Song')
        uploader = song_info.get('uploader', 'Unknown Artist')
        duration = song_info.get('duration', 0)
        thumbnail = song_info.get('thumbnail')
        url = song_info.get('webpage_url', '')
        
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**[{title}]({url})**\n🎤 by **{uploader}**",
            color=discord.Color.green()
        )
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        # Duration info
        if duration > 0:
            duration_str = f"{duration // 60}:{duration % 60:02d}"
            embed.add_field(
                name="⏱️ Duration",
                value=duration_str,
                inline=True
            )
        else:
            embed.add_field(
                name="⏱️ Duration",
                value="🔴 Live Stream",
                inline=True
            )
        
        # Volume info
        if voice_state and hasattr(voice_state, 'volume'):
            volume_percent = int(voice_state.volume * 100)
            volume_bar = ProgressBar.create_volume_bar(voice_state.volume)
            embed.add_field(
                name="🔊 Volume",
                value=f"{volume_bar} {volume_percent}%",
                inline=True
            )
        
        # Queue info
        if voice_state and hasattr(voice_state, 'songs'):
            queue_size = len(voice_state.songs)
            if queue_size > 0:
                embed.add_field(
                    name="📋 Queue",
                    value=f"{queue_size} song(s) queued",
                    inline=True
                )
        
        # Playback controls hint
        embed.add_field(
            name="🎮 Controls",
            value="`⏸️ ?pause` `⏹️ ?stop` `⏭️ ?skip` `🔊 ?volume`",
            inline=False
        )
        
        embed.set_footer(text="🎧 Enjoying the music? Use ?help for more commands!")
        return embed
    
    @staticmethod
    def create_queue_embed(songs: List, current_song: Any = None, page: int = 1, 
                          items_per_page: int = 10, playlist_info: Dict = None) -> discord.Embed:
        """Create an enhanced queue embed"""
        total_songs = len(songs)
        total_pages = math.ceil(total_songs / items_per_page) if total_songs > 0 else 1
        
        start_index = (page - 1) * items_per_page
        end_index = min(start_index + items_per_page, total_songs)
        
        embed = discord.Embed(
            title="📋 Music Queue",
            color=discord.Color.blue()
        )
        
        # Current song info
        if current_song:
            embed.add_field(
                name="▶️ Currently Playing",
                value=f"**{current_song.source.title}**\nby {current_song.source.uploader}",
                inline=False
            )
        
        # Queue content
        if total_songs == 0:
            embed.description = "📭 **Queue is empty**\nAdd songs with `?play <song name or URL>`"
        else:
            queue_text = ""
            for i in range(start_index, end_index):
                song = songs[i]
                position = i + 1
                
                # Duration
                duration = song.source.duration
                if duration > 0:
                    duration_str = f" `[{duration // 60}:{duration % 60:02d}]`"
                else:
                    duration_str = " `[LIVE]`"
                
                queue_text += f"`{position:2d}.` **{song.source.title}**{duration_str}\n"
                queue_text += f"     🎤 {song.source.uploader}\n\n"
            
            embed.description = queue_text
            
            # Page info
            if total_pages > 1:
                embed.set_footer(
                    text=f"Page {page}/{total_pages} • {total_songs} total songs • Use ?queue <page> to navigate"
                )
            else:
                embed.set_footer(text=f"{total_songs} songs in queue")
        
        # Playlist info
        if playlist_info:
            playlist_title = playlist_info.get('title', 'Unknown Playlist')
            total_playlist_songs = len(playlist_info.get('entries', []))
            
            embed.add_field(
                name="📀 Active Playlist",
                value=f"**{playlist_title}**\n{total_playlist_songs} total songs",
                inline=True
            )
        
        return embed
    
    @staticmethod
    def create_help_embed(commands_dict: Dict[str, List[str]], bot_user: discord.User = None) -> discord.Embed:
        """Create an enhanced help embed"""
        embed = discord.Embed(
            title="🎵 Music Bot - Command Help",
            description="Here are all the available commands organized by category:",
            color=discord.Color.gold()
        )
        
        if bot_user:
            embed.set_thumbnail(url=bot_user.display_avatar.url)
        
        # Add command categories
        for category, commands in commands_dict.items():
            if commands:
                embed.add_field(
                    name=f"🎯 {category}",
                    value="\n".join(commands),
                    inline=False
                )
        
        # Usage tips
        embed.add_field(
            name="💡 Pro Tips",
            value="""
            • Use `?play` with song names or YouTube/Spotify/SoundCloud URLs
            • Create playlists with `?play <playlist_url>`
            • Use `?skip` or react with ⏭️ to skip songs
            • Adjust volume with `?volume <0-100>`
            • Use `?queue` to see what's coming up next
            """,
            inline=False
        )
        
        embed.set_footer(
            text="🎧 For detailed help on a specific command, use ?help <command>"
        )
        
        return embed

class InteractionEnhancer:
    """Enhanced user interactions and feedback"""
    
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
    
    async def create_confirmation_prompt(self, message: str, timeout: int = 30) -> Optional[bool]:
        """Create a confirmation prompt with reactions"""
        embed = discord.Embed(
            title="🤔 Confirmation Required",
            description=message,
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="React to respond:",
            value="✅ Yes\n❌ No",
            inline=False
        )
        
        msg = await self.ctx.send(embed=embed)
        
        # Add reactions
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        def check(reaction, user):
            return (user == self.ctx.author and 
                   str(reaction.emoji) in ["✅", "❌"] and 
                   reaction.message.id == msg.id)
        
        try:
            reaction, user = await self.ctx.bot.wait_for('reaction_add', timeout=timeout, check=check)
            
            result = str(reaction.emoji) == "✅"
            
            # Update embed with result
            result_color = discord.Color.green() if result else discord.Color.red()
            result_text = "Confirmed ✅" if result else "Cancelled ❌"
            
            embed.title = f"🤔 {result_text}"
            embed.color = result_color
            
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            
            return result
            
        except asyncio.TimeoutError:
            embed.title = "🕐 Confirmation Timeout"
            embed.description = "No response received within 30 seconds."
            embed.color = discord.Color.red()
            
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            
            return None
    
    async def create_selection_menu(self, title: str, options: List[str], timeout: int = 60) -> Optional[int]:
        """Create a selection menu with numbered reactions"""
        if len(options) > 9:
            options = options[:9]  # Discord reaction limit
        
        embed = discord.Embed(
            title=f"🎯 {title}",
            description="React with a number to make your selection:",
            color=discord.Color.blue()
        )
        
        # Add options
        option_text = ""
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
        
        for i, option in enumerate(options):
            option_text += f"{number_emojis[i]} {option}\n"
        
        embed.add_field(name="Options:", value=option_text, inline=False)
        embed.add_field(name="⏰ Timeout:", value=f"{timeout} seconds", inline=True)
        
        msg = await self.ctx.send(embed=embed)
        
        # Add number reactions
        valid_reactions = []
        for i in range(len(options)):
            await msg.add_reaction(number_emojis[i])
            valid_reactions.append(number_emojis[i])
        
        # Add cancel reaction
        await msg.add_reaction("❌")
        valid_reactions.append("❌")
        
        def check(reaction, user):
            return (user == self.ctx.author and 
                   str(reaction.emoji) in valid_reactions and 
                   reaction.message.id == msg.id)
        
        try:
            reaction, user = await self.ctx.bot.wait_for('reaction_add', timeout=timeout, check=check)
            
            if str(reaction.emoji) == "❌":
                result = None
                result_text = "Selection cancelled"
                result_color = discord.Color.red()
            else:
                result = number_emojis.index(str(reaction.emoji))
                result_text = f"Selected: {options[result]}"
                result_color = discord.Color.green()
            
            # Update embed with result
            embed.title = f"🎯 {result_text}"
            embed.color = result_color
            
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            
            return result
            
        except asyncio.TimeoutError:
            embed.title = "🕐 Selection Timeout"
            embed.description = "No selection made within the time limit."
            embed.color = discord.Color.red()
            
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            
            return None
    
    async def show_success_message(self, title: str, description: str, auto_delete: int = None):
        """Show a success message with optional auto-delete"""
        embed = discord.Embed(
            title=f"✅ {title}",
            description=description,
            color=discord.Color.green()
        )
        
        if auto_delete:
            embed.set_footer(text=f"This message will be deleted in {auto_delete} seconds")
        
        msg = await self.ctx.send(embed=embed)
        
        if auto_delete:
            await asyncio.sleep(auto_delete)
            try:
                await msg.delete()
            except discord.NotFound:
                pass
    
    async def show_error_message(self, title: str, description: str, suggestion: str = None):
        """Show an error message with optional suggestion"""
        embed = discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=discord.Color.red()
        )
        
        if suggestion:
            embed.add_field(
                name="💡 Suggestion",
                value=suggestion,
                inline=False
            )
        
        embed.set_footer(text="Need help? Use ?help for available commands")
        
        await self.ctx.send(embed=embed)

class SmartPlaybackFeedback:
    """Smart feedback system for music playback"""
    
    @staticmethod
    async def send_song_added_feedback(ctx: commands.Context, song_info: Dict[str, Any], 
                                     queue_position: int = None, is_playing_now: bool = False):
        """Send enhanced feedback when a song is added"""
        title = song_info.get('title', 'Unknown Song')
        uploader = song_info.get('uploader', 'Unknown Artist')
        duration = song_info.get('duration', 0)
        thumbnail = song_info.get('thumbnail')
        
        if is_playing_now:
            embed = discord.Embed(
                title="▶️ Now Playing",
                description=f"**{title}**\nby {uploader}",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="✅ Song Added to Queue",
                description=f"**{title}**\nby {uploader}",
                color=discord.Color.blue()
            )
            
            if queue_position:
                embed.add_field(
                    name="📍 Queue Position",
                    value=f"#{queue_position}",
                    inline=True
                )
        
        # Duration
        if duration > 0:
            duration_str = f"{duration // 60}:{duration % 60:02d}"
            embed.add_field(
                name="⏱️ Duration",
                value=duration_str,
                inline=True
            )
        else:
            embed.add_field(
                name="⏱️ Duration",
                value="🔴 Live",
                inline=True
            )
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        embed.set_footer(text="🎵 Use ?queue to see the full queue")
        
        await ctx.send(embed=embed)
    
    @staticmethod
    async def send_playlist_added_feedback(ctx: commands.Context, playlist_info: Dict[str, Any], 
                                         songs_loaded: int, total_songs: int):
        """Send enhanced feedback when a playlist is added"""
        playlist_title = playlist_info.get('title', 'Unknown Playlist')
        
        embed = discord.Embed(
            title="📀 Playlist Added",
            description=f"**{playlist_title}**",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="📊 Songs Loaded",
            value=f"{songs_loaded}/{total_songs}",
            inline=True
        )
        
        if songs_loaded < total_songs:
            remaining = total_songs - songs_loaded
            embed.add_field(
                name="⏳ Auto-Loading",
                value=f"{remaining} more songs will load automatically",
                inline=True
            )
        
        # Progress bar for loading
        if total_songs > 0:
            progress = songs_loaded / total_songs
            progress_bar = ProgressBar.create_bar(progress, 20)
            embed.add_field(
                name="📈 Loading Progress",
                value=f"{progress_bar} {int(progress * 100)}%",
                inline=False
            )
        
        embed.set_footer(text="🎵 Use ?queue to see all loaded songs")
        
        await ctx.send(embed=embed)

# Utility functions for UI enhancements
def format_duration(seconds: int) -> str:
    """Format duration in a user-friendly way"""
    if seconds <= 0:
        return "🔴 Live"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

def format_file_size(bytes_size: int) -> str:
    """Format file size in a user-friendly way"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"

def format_time_ago(timestamp: float) -> str:
    """Format timestamp as 'X time ago'"""
    now = time.time()
    diff = int(now - timestamp)
    
    if diff < 60:
        return f"{diff} second(s) ago"
    elif diff < 3600:
        return f"{diff // 60} minute(s) ago"
    elif diff < 86400:
        return f"{diff // 3600} hour(s) ago"
    else:
        return f"{diff // 86400} day(s) ago"

def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis if too long"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."