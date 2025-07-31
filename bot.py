import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import yt_dlp
import asyncio
import functools
import itertools
import math
import random


# Load environment variables
load_dotenv('token.env')

# Bot configuration
PREFIX = '?'
TOKEN = os.getenv('TOKEN')

# Check if token is available
if not TOKEN:
    print("❌ ERROR: Discord bot token not found!")
    print("🔧 For local development: Make sure 'token.env' file exists with TOKEN=your_bot_token")
    print("☁️ For hosting: Set TOKEN environment variable in your hosting platform")
    print("🔗 Get your token from: https://discord.com/developers/applications")
    exit(1)

# FFmpeg options
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# FFmpeg executable path (local first, then system for hosting platforms)
import shutil
import os

# Try to use local FFmpeg first, then system FFmpeg
def get_ffmpeg_executable():
    # Check local ffmpeg folder first
    local_ffmpeg = os.path.join(os.path.dirname(__file__), 'ffmpeg', 'ffmpeg.exe')
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg
    
    # Fall back to system FFmpeg (for hosting platforms)
    return shutil.which('ffmpeg') or 'ffmpeg'

FFMPEG_EXECUTABLE = get_ffmpeg_executable()

# yt-dlp options (Optimized for speed)
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,  # Enable playlist support
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'extractaudio': True,
    'audioformat': 'mp3',
    'audioquality': '192K',
    # Speed optimizations
    'socket_timeout': 10,        # Faster timeout for slow sources
    'retries': 2,               # Fewer retries for faster loading
    'fragment_retries': 2,      # Fewer fragment retries
    'skip_unavailable_fragments': True,  # Skip problematic fragments
}

class VoiceError(Exception):
    pass

class YTDLError(Exception):
    pass

class YTDLSource(discord.PCMVolumeTransformer):
    YTDL = yt_dlp.YoutubeDL(YDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4] if date else None
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration', 0)))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.YTDL.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        # Get webpage URL - handle different possible keys
        webpage_url = process_info.get('webpage_url')
        if not webpage_url:
            webpage_url = process_info.get('url')
        if not webpage_url and 'id' in process_info:
            # Construct URL from ID for YouTube/YouTube Music
            webpage_url = f"https://www.youtube.com/watch?v={process_info['id']}"
        if not webpage_url:
            # Last resort - use the original search term
            webpage_url = search
            
        partial = functools.partial(cls.YTDL.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))

        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **FFMPEG_OPTIONS, executable=FFMPEG_EXECUTABLE), data=info)
    
    @classmethod
    async def extract_playlist_info(cls, url: str, *, loop: asyncio.BaseEventLoop = None):
        """Extract playlist information without downloading"""
        loop = loop or asyncio.get_event_loop()
        
        # Create YTDL instance with playlist enabled - don't use extract_flat for URLs
        ytdl_playlist = yt_dlp.YoutubeDL({
            **YDL_OPTIONS,
            'extract_flat': False,  # Need full URLs for each entry
            'noplaylist': False,    # Ensure playlists are processed
            'quiet': True,          # Reduce output
            'no_warnings': True,
        })
        
        partial = functools.partial(ytdl_playlist.extract_info, url, download=False, process=False)
        data = await loop.run_in_executor(None, partial)
        
        if data is None:
            raise YTDLError('Couldn\'t extract playlist information from `{}`'.format(url))
            
        # Convert entries generator to list if needed
        if 'entries' in data:
            entries_list = list(data['entries']) if hasattr(data['entries'], '__iter__') else data['entries']
            data['entries'] = entries_list
        
        # Check if it's actually a playlist
        if 'entries' not in data or len(data.get('entries', [])) <= 1:
            return None  # Not a playlist or single video
        
        # Filter out None entries and ensure we have valid entries
        valid_entries = []
        for entry in data['entries']:
            if entry and ('url' in entry or 'webpage_url' in entry or 'id' in entry):
                # Ensure we have a proper URL
                if 'webpage_url' not in entry and 'id' in entry:
                    # Construct URL from ID for YouTube/YouTube Music
                    if 'youtube.com' in url or 'music.youtube.com' in url:
                        entry['webpage_url'] = f"https://www.youtube.com/watch?v={entry['id']}"
                    else:
                        entry['webpage_url'] = entry.get('url', entry.get('id'))
                elif 'webpage_url' not in entry and 'url' in entry:
                    entry['webpage_url'] = entry['url']
                valid_entries.append(entry)
        
        if not valid_entries:
            raise YTDLError('No valid entries found in playlist')
            
        data['entries'] = valid_entries
        return data
    
    @classmethod
    async def is_playlist(cls, url: str) -> bool:
        """Check if the given URL is a playlist"""
        try:
            playlist_data = await cls.extract_playlist_info(url)
            return playlist_data is not None
        except:
            return False

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days:
            duration.append(f'{days}d')
        if hours:
            duration.append(f'{hours}h')
        if minutes:
            duration.append(f'{minutes}m')
        if seconds:
            duration.append(f'{seconds}s')

        return ':'.join(duration) if duration else '0s'

class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = (discord.Embed(title='Now playing',
                               description='```css\n{0.source.title}\n```'.format(self),
                               color=discord.Color.blurple())
                 .add_field(name='Duration', value=self.source.duration)
                 .add_field(name='Requested by', value=self.requester.mention)
                 .add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .add_field(name='URL', value='[Click]({0.source.url})'.format(self))
                 .set_thumbnail(url=self.source.thumbnail))

        return embed

class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]

class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()

        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()
        
        # Auto-disconnect timer
        self.disconnect_timer = None
        
        # Playlist auto-continue support
        self.current_playlist = None  # Stores playlist info
        self.playlist_position = 0    # Current position in playlist
        self.playlist_batch_size = 15 # Songs to load per batch (reduced for faster loading)
        self.playlist_low_threshold = 3 # When to load next batch (reduced for more frequent loading)
        self.concurrent_load_limit = 4 # Max songs to load simultaneously
        self._background_loading = False  # Flag to prevent multiple background loads

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        """Main audio player loop with enhanced error handling and recovery"""
        print(f"🎵 Audio player task started for guild {self._ctx.guild.id}")
        
        while True:
            try:
                self.next.clear()

                # Check voice connection before proceeding
                if not self.voice or not self.voice.is_connected():
                    print("⚠️ Voice connection lost, stopping audio player")
                    self.bot.loop.create_task(self.stop())
                    return

                if not self.loop:
                    # Try to get the next song within 3 minutes.
                    # If no song will be added to the queue in time,
                    # the player will disconnect due to performance
                    # reasons.
                    try:
                        async with asyncio.timeout(180):  # 3 minutes
                            self.current = await self.songs.get()
                            print(f"🎵 Got next song: {self.current.source.title}")
                    except asyncio.TimeoutError:
                        print("⏰ Timeout waiting for next song")
                        # Before giving up, check if we can auto-load from playlist
                        if self.current_playlist and len(self.songs) == 0:
                            await self.check_playlist_auto_load()
                            # Try one more time to get a song
                            try:
                                async with asyncio.timeout(30):  # Short timeout
                                    self.current = await self.songs.get()
                                    print(f"🎵 Got song after auto-load: {self.current.source.title}")
                            except asyncio.TimeoutError:
                                print("⏰ Final timeout, stopping player")
                                self.bot.loop.create_task(self.stop())
                                return
                        else:
                            print("⏰ No playlist auto-load available, stopping player")
                            self.bot.loop.create_task(self.stop())
                            return
                    
                    # After getting a song, check if we need to auto-load more (for future)
                    await self.check_playlist_auto_load()
                else:
                    # When looping, we need to recreate the audio source
                    # because FFmpeg sources can't be reused
                    print(f"🔄 Looping song: {self.current.source.title}")
                    if self.current and hasattr(self.current.source, 'data'):
                        try:
                            # Get the stream URL from the song data
                            audio_url = self.current.source.data.get('url')
                            if audio_url:
                                # Create a new FFmpeg audio source
                                new_audio_source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS, executable=FFMPEG_EXECUTABLE)
                                
                                # Replace the old audio source in the YTDLSource
                                old_volume = self.current.source.volume
                                self.current.source.original = new_audio_source
                                self.current.source.volume = old_volume  # Preserve volume
                                print("✅ Successfully recreated audio source for loop")
                            else:
                                # If we can't get the URL, disable loop and continue
                                self.loop = False
                                await self.current.source.channel.send("⚠️ Cannot loop this song - no stream URL available")
                                print("❌ No audio URL for looping")
                        except Exception as e:
                            # If recreation fails, disable loop and continue
                            self.loop = False
                            await self.current.source.channel.send("⚠️ Loop failed - continuing to next song")
                            print(f"❌ Loop recreation failed: {e}")

                # Set volume and start playing
                self.current.source.volume = self._volume
                
                # Double-check voice connection before playing
                if not self.voice or not self.voice.is_connected():
                    print("⚠️ Voice connection lost before playing, stopping")
                    self.bot.loop.create_task(self.stop())
                    return
                
                print(f"▶️ Starting playback: {self.current.source.title}")
                self.voice.play(self.current.source, after=self.play_next_song)
                
                # Send enhanced "Now Playing" message
                embed = self.current.create_embed()
                
                # Add playlist info if active
                if self.current_playlist:
                    total_songs = len(self.current_playlist['entries'])
                    playlist_title = self.current_playlist.get('title', 'Unknown Playlist')
                    queue_count = len(self.songs)
                    
                    # Calculate remaining: total songs - currently playing - in queue
                    processed_songs = self.playlist_position  # Songs we've attempted to load
                    remaining = total_songs - processed_songs
                    
                    # If we have songs in queue, show that info
                    if queue_count > 0 or remaining > 0:
                        embed.add_field(
                            name="📀 From Playlist",
                            value=f"**{playlist_title}**\n{queue_count} in queue • {remaining} remaining",
                            inline=False
                        )
                
                await self.current.source.channel.send("🎵 **Now Playing:**", embed=embed)

                await self.next.wait()
                
            except Exception as e:
                print(f"❌ Critical error in audio_player_task: {e}")
                # Try to send error message to channel
                try:
                    if hasattr(self, '_ctx') and self._ctx:
                        await self._ctx.send(f"⚠️ Audio player error: {str(e)}\nRestarting player...")
                except:
                    pass
                
                # Clear current song and continue
                self.current = None
                await asyncio.sleep(2)  # Brief pause before continuing
                continue

    def play_next_song(self, error=None):
        if error:
            # Handle common FFmpeg errors more gracefully
            error_str = str(error)
            if "'_MissingSentinel' object has no attribute 'read'" in error_str:
                print("FFmpeg audio source error - likely due to stream expiration during loop")
                # Don't raise the error, just continue to next song
                self.loop = False  # Disable loop to prevent repeated errors
            elif "ffmpeg" in error_str.lower() or "audio" in error_str.lower():
                print(f"Audio playback error: {error_str}")
                # Don't crash the bot, just continue
            else:
                # For other unexpected errors, still raise them
                raise VoiceError(str(error))

        self.next.set()

    def skip(self):
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()
        
        # Cancel disconnect timer if it exists
        if self.disconnect_timer:
            self.disconnect_timer.cancel()
            self.disconnect_timer = None

        if self.voice:
            await self.voice.disconnect()
            self.voice = None
    
    def start_disconnect_timer(self):
        """Start a timer to disconnect if bot is alone for too long"""
        if self.disconnect_timer:
            self.disconnect_timer.cancel()
        
        # Disconnect after 5 minutes of being alone
        self.disconnect_timer = self.bot.loop.create_task(self._disconnect_after_delay())
    
    def cancel_disconnect_timer(self):
        """Cancel the disconnect timer when users rejoin"""
        if self.disconnect_timer:
            self.disconnect_timer.cancel()
            self.disconnect_timer = None
    
    async def _disconnect_after_delay(self):
        """Internal method to handle delayed disconnection"""
        try:
            await asyncio.sleep(300)  # Wait 5 minutes
            
            # Double-check that bot is still alone before disconnecting
            if self.voice and len(self.voice.channel.members) == 1:  # Only bot in channel
                await self._ctx.send("🔌 Left voice channel due to inactivity (5 minutes alone)")
                await self.stop()
        except asyncio.CancelledError:
            pass  # Timer was cancelled, which is expected
    
    async def load_songs_concurrently(self, entries_batch, loading_msg=None, update_progress=True):
        """Load multiple songs concurrently for better performance"""
        if not entries_batch:
            return 0, 0
        
        # Split into smaller concurrent batches to avoid overwhelming
        concurrent_batches = []
        for i in range(0, len(entries_batch), self.concurrent_load_limit):
            batch = entries_batch[i:i + self.concurrent_load_limit]
            concurrent_batches.append(batch)
        
        total_loaded = 0
        total_failed = 0
        
        for batch_idx, batch in enumerate(concurrent_batches):
            # Update progress
            if loading_msg and update_progress:
                processed = batch_idx * self.concurrent_load_limit
                total_in_batch = len(entries_batch)
                await loading_msg.edit(content=f'⚡ Fast-loading songs... {processed}/{total_in_batch}')
            
            # Create concurrent tasks for this batch
            tasks = []
            for entry in batch:
                if entry and ('webpage_url' in entry):
                    task = self._load_single_song_safe(entry['webpage_url'])
                    tasks.append(task)
            
            if not tasks:
                continue
                
            # Execute all tasks concurrently
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in results:
                    if isinstance(result, Exception):
                        # Handle failed song loading
                        error_str = str(result)
                        if any(error_msg in error_str.lower() for error_msg in [
                            'video unavailable', 'video is not available', 'private video',
                            'deleted video', 'video has been removed', 'forbidden'
                        ]):
                            total_failed += 1  # Silent fail for common errors
                        else:
                            print(f"Song loading error: {error_str}")
                            total_failed += 1
                    elif result is not None:
                        # Successfully loaded song
                        await self.songs.put(result)
                        total_loaded += 1
                        
            except Exception as e:
                print(f"Batch loading error: {e}")
                total_failed += len(tasks)
        
        return total_loaded, total_failed
    
    async def _load_single_song_safe(self, url):
        """Safely load a single song with error handling"""
        try:
            source = await YTDLSource.create_source(self._ctx, url, loop=self.bot.loop)
            return Song(source)
        except Exception as e:
            # Re-raise the exception to be handled by the caller
            raise e
    
    async def check_playlist_auto_load(self):
        """Check if we need to auto-load more songs from current playlist"""
        if not self.current_playlist:
            return  # No active playlist
            
        # Check if queue is getting low
        if len(self.songs) <= self.playlist_low_threshold:
            # Check if there are more songs to load
            total_songs = len(self.current_playlist['entries'])
            if self.playlist_position < total_songs:
                await self.load_next_playlist_batch()
        
        # Also start background loading if queue is getting low and we're not already loading
        elif len(self.songs) <= self.playlist_low_threshold + 2 and not self._background_loading:
            total_songs = len(self.current_playlist['entries'])
            if self.playlist_position < total_songs:
                # Start background loading without blocking current playback
                self.bot.loop.create_task(self._background_load_next_batch())
    
    async def load_next_playlist_batch(self):
        """Load the next batch of songs from the current playlist using concurrent loading"""
        if not self.current_playlist:
            return
            
        entries = self.current_playlist['entries']
        start_pos = self.playlist_position
        end_pos = min(start_pos + self.playlist_batch_size, len(entries))
        
        if start_pos >= len(entries):
            return  # No more songs to load
            
        batch_entries = entries[start_pos:end_pos]
        batch_size = len(batch_entries)
        
        # Show loading message for larger batches
        if batch_size > 3:
            loading_msg = await self._ctx.send(f"⚡ Fast-loading {batch_size} more songs from playlist...")
        else:
            loading_msg = None
        
        # Use concurrent loading for much better performance
        loaded_count, failed_count = await self.load_songs_concurrently(
            batch_entries, loading_msg, update_progress=True
        )
        
        self.playlist_position = end_pos
        
        if loaded_count > 0:
            remaining = len(entries) - self.playlist_position
            success_msg = f"⚡ **Fast-loaded {loaded_count} more songs**"
            if remaining > 0:
                success_msg += f" ({remaining} remaining)"
            if failed_count > 0:
                success_msg += f" • Skipped {failed_count} unavailable"
                
            if loading_msg:
                await loading_msg.edit(content=success_msg)
            else:
                await self._ctx.send(success_msg)
    
    async def _background_load_next_batch(self):
        """Load next batch in background without interrupting playback"""
        if self._background_loading:
            return  # Already loading in background
            
        self._background_loading = True
        try:
            # Load next batch silently in background
            if self.current_playlist and self.playlist_position < len(self.current_playlist['entries']):
                entries = self.current_playlist['entries']
                start_pos = self.playlist_position
                end_pos = min(start_pos + self.playlist_batch_size, len(entries))
                
                if start_pos < len(entries):
                    batch_entries = entries[start_pos:end_pos]
                    
                    # Load concurrently but silently (no loading messages)
                    loaded_count, failed_count = await self.load_songs_concurrently(
                        batch_entries, loading_msg=None, update_progress=False
                    )
                    
                    self.playlist_position = end_pos
                    
                    # Only show message if we successfully loaded songs
                    if loaded_count > 0:
                        remaining = len(entries) - self.playlist_position  
                        success_msg = f"🔄 Background-loaded {loaded_count} more songs"
                        if remaining > 0:
                            success_msg += f" ({remaining} remaining)"
                        if failed_count > 0:
                            success_msg += f" • Skipped {failed_count} unavailable"
                        
                        # Send a brief, non-intrusive message
                        await self._ctx.send(success_msg)
                        
        except Exception as e:
            print(f"Background loading error: {e}")
        finally:
            self._background_loading = False
    
    def set_playlist(self, playlist_data):
        """Set the current playlist for auto-continuation"""
        self.current_playlist = playlist_data
        self.playlist_position = 0
    
    def clear_playlist(self):
        """Clear the current playlist"""
        self.current_playlist = None
        self.playlist_position = 0

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send('An error occurred: {}'.format(str(error)))

    @commands.command(name='join', invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        """Joins a voice channel."""

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='summon')
    @commands.has_permissions(manage_guild=True)
    async def _summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        """Summons the bot to a voice channel.
        If no channel was specified, it joins your channel.
        """

        if not channel and not ctx.author.voice:
            raise VoiceError('You are neither connected to a voice channel nor specified a channel to join.')

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command(name='leave', aliases=['disconnect'])
    @commands.has_permissions(manage_guild=True)
    async def _leave(self, ctx: commands.Context):
        """Clears the queue and leaves the voice channel."""

        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.command(name='volume', aliases=['vol'])
    async def _volume(self, ctx: commands.Context, volume: int = None):
        """Sets the volume of the player or shows current volume."""

        if not ctx.voice_state.is_playing:
            return await ctx.send('🔊 Nothing being played at the moment.')

        # If no volume provided, show current volume
        if volume is None:
            current_vol = int(ctx.voice_state.volume * 100)
            volume_bar = "█" * (current_vol // 5) + "░" * (20 - (current_vol // 5))
            return await ctx.send(f'🔊 Current volume: **{current_vol}%**\n`{volume_bar}` {current_vol}%')

        if volume < 0 or volume > 100:
            return await ctx.send('🔊 Volume must be between 0 and 100')

        # Set the volume for the voice state (affects future songs)
        ctx.voice_state.volume = volume / 100
        
        # Also apply to currently playing song immediately
        if ctx.voice_state.current and ctx.voice_state.current.source:
            ctx.voice_state.current.source.volume = volume / 100

        # Send confirmation with volume bar visualization
        volume_bar = "█" * (volume // 5) + "░" * (20 - (volume // 5))
        await ctx.send(f'🔊 Volume set to **{volume}%**\n`{volume_bar}` {volume}%')

    @commands.command(name='now', aliases=['current', 'playing'])
    async def _now(self, ctx: commands.Context):
        """Displays the currently playing song."""

        await ctx.send(embed=ctx.voice_state.current.create_embed())

    @commands.command(name='pause')
    @commands.has_permissions(manage_guild=True)
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.message.add_reaction('⏯️')

    @commands.command(name='resume')
    @commands.has_permissions(manage_guild=True)
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.message.add_reaction('⏯️')

    @commands.command(name='stop')
    @commands.has_permissions(manage_guild=True)
    async def _stop(self, ctx: commands.Context):
        """Stops playing song and clears the queue."""

        ctx.voice_state.songs.clear()
        ctx.voice_state.clear_playlist()  # Clear current playlist

        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            await ctx.message.add_reaction('⏹️')

    @commands.command(name='skip')
    async def _skip(self, ctx: commands.Context):
        """Vote to skip a song. The requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Not playing any music right now...')

        voter = ctx.message.author
        if voter == ctx.voice_state.current.requester:
            await ctx.message.add_reaction('⏭️')
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 3:
                await ctx.message.add_reaction('⏭️')
                ctx.voice_state.skip()
            else:
                await ctx.send('Skip vote added, currently **{}/3**'.format(total_votes))

        else:
            await ctx.send('You have already voted to skip this song.')

    @commands.command(name='queue', aliases=['q'])
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        """Shows the player's queue.
        You can optionally specify the page to show. Each page contains 10 elements.
        """

        if len(ctx.voice_state.songs) == 0:
            # Check if there's an active playlist but no loaded songs yet
            if ctx.voice_state.current_playlist:
                total_playlist_songs = len(ctx.voice_state.current_playlist['entries'])
                playlist_title = ctx.voice_state.current_playlist.get('title', 'Unknown Playlist')
                return await ctx.send(f'📋 **Queue is empty but playlist is active:**\n'
                                    f'🎵 **{playlist_title}** ({total_playlist_songs} total songs)\n'
                                    f'⏳ Songs will load automatically as needed')
            else:
                return await ctx.send('📋 Queue is empty.')

        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)

        start = (page - 1) * items_per_page
        end = start + items_per_page

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += '`{0}.` [**{1.source.title}**]({1.source.url})\n'.format(i + 1, song)

        # Add playlist info if active
        playlist_info = ""
        if ctx.voice_state.current_playlist:
            total_playlist_songs = len(ctx.voice_state.current_playlist['entries'])
            loaded_songs = ctx.voice_state.playlist_position
            remaining_songs = total_playlist_songs - loaded_songs
            playlist_title = ctx.voice_state.current_playlist.get('title', 'Unknown Playlist')
            
            if remaining_songs > 0:
                playlist_info = f'\n📀 **Playlist**: {playlist_title}\n🔄 {remaining_songs} more songs will auto-load'

        embed = (discord.Embed(
            title="📋 Music Queue", 
            description='**{} tracks in queue:**\n\n{}{}'.format(len(ctx.voice_state.songs), queue, playlist_info),
            color=discord.Color.blue()
        ).set_footer(text='Viewing page {}/{}'.format(page, pages)))
        
        await ctx.send(embed=embed)

    @commands.command(name='shuffle')
    async def _shuffle(self, ctx: commands.Context):
        """Shuffles the current queue. Note: This only shuffles loaded songs, not the entire playlist."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('📋 Queue is empty - nothing to shuffle.')

        ctx.voice_state.songs.shuffle()
        
        # Add extra info if playlist is active
        if ctx.voice_state.current_playlist:
            remaining = len(ctx.voice_state.current_playlist['entries']) - ctx.voice_state.playlist_position
            if remaining > 0:
                await ctx.send(f'🔀 Shuffled {len(ctx.voice_state.songs)} songs in queue\n'
                             f'📀 {remaining} more songs will load in original playlist order')
            else:
                await ctx.message.add_reaction('🔀')
        else:
            await ctx.message.add_reaction('🔀')

    @commands.command(name='remove')
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a song from the queue at a given index."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.message.add_reaction('✅')

    @commands.command(name='loop')
    async def _loop(self, ctx: commands.Context):
        """Loops the currently playing song.
        Invoke this command again to unloop the song.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Nothing being played at the moment.')

        # Inverse boolean value to loop and unloop.
        ctx.voice_state.loop = not ctx.voice_state.loop
        
        if ctx.voice_state.loop:
            await ctx.send('🔂 **Loop enabled** - Current song will repeat')
        else:
            await ctx.send('➡️ **Loop disabled** - Playlist/Song will continue normally')
    
    @commands.command(name='playlist', aliases=['pl'])
    async def _playlist(self, ctx: commands.Context):
        """Shows current playlist status and information."""
        
        if not ctx.voice_state.current_playlist:
            return await ctx.send('📋 No active playlist - use `?play <playlist_url>` to load one')
        
        playlist_data = ctx.voice_state.current_playlist
        playlist_title = playlist_data.get('title', 'Unknown Playlist')
        total_songs = len(playlist_data['entries'])
        loaded_songs = ctx.voice_state.playlist_position
        queue_songs = len(ctx.voice_state.songs)
        remaining_songs = total_songs - loaded_songs
        
        embed = discord.Embed(
            title="📀 Current Playlist",
            description=f"**{playlist_title}**",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Progress",
            value=f"**Total Songs:** {total_songs}\n"
                  f"**Loaded:** {loaded_songs}\n"
                  f"**In Queue:** {queue_songs}\n"
                  f"**Remaining:** {remaining_songs}",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Auto-Loading",
            value=f"**Batch Size:** {ctx.voice_state.playlist_batch_size}\n"
                  f"**Load When:** {ctx.voice_state.playlist_low_threshold} songs left\n"
                  f"**Status:** {'Active' if remaining_songs > 0 else 'Complete'}",
            inline=True
        )
        
        if remaining_songs > 0:
            embed.set_footer(text="Songs will auto-load when queue gets low")
        else:
            embed.set_footer(text="All playlist songs have been loaded")
        
        await ctx.send(embed=embed)

    @commands.command(name='debug', aliases=['status'])
    async def _debug(self, ctx: commands.Context):
        """Shows bot status and debug information."""
        
        voice_state = ctx.voice_state
        
        embed = discord.Embed(
            title="🔧 Bot Debug Status",
            color=discord.Color.blue()
        )
        
        # Voice Connection Status
        voice_status = "❌ Not Connected"
        if voice_state.voice:
            if voice_state.voice.is_connected():
                voice_status = f"✅ Connected to {voice_state.voice.channel.name}"
            else:
                voice_status = "⚠️ Disconnected"
        
        embed.add_field(
            name="🔊 Voice Connection",
            value=voice_status,
            inline=False
        )
        
        # Audio Player Status
        player_status = "❌ Not Running"
        if hasattr(voice_state, 'audio_player') and voice_state.audio_player:
            if voice_state.audio_player.done():
                player_status = "💀 Crashed/Stopped"
            elif voice_state.audio_player.cancelled():
                player_status = "⏹️ Cancelled"
            else:
                player_status = "✅ Running"
        
        embed.add_field(
            name="🎵 Audio Player Task",
            value=player_status,
            inline=True
        )
        
        # Current Song Status
        current_status = "❌ None"
        if voice_state.current:
            current_status = f"🎵 {voice_state.current.source.title[:30]}..."
        
        embed.add_field(
            name="▶️ Current Song",
            value=current_status,
            inline=True
        )
        
        # Queue Status
        queue_count = len(voice_state.songs)
        queue_status = f"📝 {queue_count} songs"
        if queue_count == 0:
            queue_status = "📝 Empty"
        
        embed.add_field(
            name="📋 Queue",
            value=queue_status,
            inline=True
        )
        
        # Playing Status
        is_playing = "❌ No"
        if voice_state.voice and voice_state.voice.is_playing():
            is_playing = "✅ Yes"
        elif voice_state.voice and voice_state.voice.is_paused():
            is_playing = "⏸️ Paused"
        
        embed.add_field(
            name="🎶 Is Playing",
            value=is_playing,
            inline=True
        )
        
        # Loop Status
        loop_status = "🔁 On" if voice_state.loop else "➡️ Off"
        embed.add_field(
            name="🔄 Loop",
            value=loop_status,
            inline=True
        )
        
        # Volume
        volume_status = f"🔊 {int(voice_state.volume * 100)}%"
        embed.add_field(
            name="📢 Volume",
            value=volume_status,
            inline=True
        )
        
        embed.set_footer(text="Use ?fix if audio player is stuck")
        
        await ctx.send(embed=embed)

    @commands.command(name='fix', aliases=['restart'])
    async def _fix(self, ctx: commands.Context):
        """Restart the audio player if it gets stuck."""
        
        voice_state = ctx.voice_state
        
        # Check if there are songs in queue but nothing playing
        queue_count = len(voice_state.songs)
        is_playing = voice_state.voice and voice_state.voice.is_playing()
        
        embed = discord.Embed(title="🔧 Audio Player Fix", color=discord.Color.orange())
        
        if not voice_state.voice or not voice_state.voice.is_connected():
            embed.description = "❌ Not connected to voice channel. Use `?join` first."
            embed.color = discord.Color.red()
            return await ctx.send(embed=embed)
        
        # Stop current playback if any
        if voice_state.voice.is_playing():
            voice_state.voice.stop()
            embed.add_field(name="⏹️ Step 1", value="Stopped current playback", inline=False)
        
        # Cancel and restart audio player task
        if hasattr(voice_state, 'audio_player') and voice_state.audio_player:
            voice_state.audio_player.cancel()
            embed.add_field(name="🔄 Step 2", value="Cancelled old audio player task", inline=False)
        
        # Create new audio player task
        voice_state.audio_player = ctx.bot.loop.create_task(voice_state.audio_player_task())
        embed.add_field(name="✅ Step 3", value="Started new audio player task", inline=False)
        
        # Check if there are songs to play
        if queue_count > 0:
            embed.add_field(name="🎵 Result", value=f"Audio player restarted! {queue_count} songs in queue should start playing.", inline=False)
            embed.color = discord.Color.green()
        else:
            embed.add_field(name="📝 Result", value="Audio player restarted, but queue is empty. Add songs with `?play`", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name='play', aliases=['p'])
    async def _play(self, ctx: commands.Context, *, search: str):
        """Plays a song or playlist.
        If there are songs in the queue, this will be queued until the
        other songs finished playing.
        This command automatically searches from various sites if no URL is provided.
        For playlists, it will load songs in batches and auto-continue.
        A list of supported sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """

        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            # Check if it's a playlist URL (YouTube or YouTube Music)
            if search.startswith(('http://', 'https://')) and self._is_playlist_url(search):
                try:
                    # Try to extract playlist info
                    playlist_data = await YTDLSource.extract_playlist_info(search, loop=self.bot.loop)
                    
                    if playlist_data and len(playlist_data.get('entries', [])) > 1:
                        # It's a playlist! Handle playlist loading
                        await self._handle_playlist(ctx, playlist_data)
                        return
                except Exception as e:
                    print(f"Failed to extract playlist, trying as single video: {e}")
                    # Fall through to single song handling
            
            # Single song handling (original behavior)
            try:
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await ctx.send('An error occurred while processing this request: {}'.format(str(e)))
            else:
                song = Song(source)
                await ctx.voice_state.songs.put(song)
                await ctx.send('🎵 Enqueued {}'.format(str(source)))
    
    async def _handle_playlist(self, ctx: commands.Context, playlist_data):
        """Handle playlist loading with smart concurrent batching"""
        total_songs = len(playlist_data['entries'])
        playlist_title = playlist_data.get('title', 'Unknown Playlist')
        
        # Set the playlist for auto-continuation
        ctx.voice_state.set_playlist(playlist_data)
        
        # Load first batch concurrently for much faster performance
        first_batch_size = min(ctx.voice_state.playlist_batch_size, total_songs)
        first_batch = playlist_data['entries'][:first_batch_size]
        
        loading_msg = await ctx.send(f'⚡ **Fast-loading playlist**: {playlist_title}\n🚀 Processing {first_batch_size} songs concurrently...')
        
        # Use concurrent loading for much better performance
        loaded_count, failed_count = await ctx.voice_state.load_songs_concurrently(
            first_batch, loading_msg, update_progress=True
        )
        
        ctx.voice_state.playlist_position = first_batch_size
        
        # Send final confirmation message
        remaining = total_songs - loaded_count
        if remaining > 0:
            final_msg = f'⚡ **Playlist Added**: {playlist_title}\n🚀 **Fast-loaded {loaded_count} songs** • {remaining} more will auto-load as needed'
            if failed_count > 0:
                final_msg += f'\n⚠️ Skipped {failed_count} unavailable songs'
        else:
            final_msg = f'⚡ **Playlist Added**: {playlist_title}\n🚀 **Fast-loaded all {loaded_count} songs**'
            if failed_count > 0:
                final_msg += f'\n⚠️ Skipped {failed_count} unavailable songs'
                
        await loading_msg.edit(content=final_msg)
    
    def _is_playlist_url(self, url: str) -> bool:
        """Check if URL is a playlist from YouTube or YouTube Music"""
        url = url.lower()
        
        # Check for common playlist indicators
        playlist_indicators = [
            'list=',                    # General playlist parameter
            'playlist?',                # Direct playlist URL
            '/playlist',                # Playlist path
            'music.youtube.com'         # YouTube Music (often has playlists)
        ]
        
        # YouTube Music specific patterns
        youtube_music_patterns = [
            'music.youtube.com/playlist',
            'music.youtube.com/watch',  # Can be playlist if has list= parameter
        ]
        
        # Check for any playlist indicators
        for indicator in playlist_indicators:
            if indicator in url:
                return True
                
        # Special handling for YouTube Music watch URLs with list parameter
        if 'music.youtube.com/watch' in url and 'list=' in url:
            return True
            
        return False

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Bot is already in a voice channel.')

# Events
@bot.event
async def on_ready():
    # Add the Music cog when bot is ready
    await bot.add_cog(Music(bot))
    
    # Set bot status
    activity = discord.Activity(type=discord.ActivityType.listening, name="?help")
    await bot.change_presence(activity=activity)
    
    print(f'✅ Bot ready! Logged in as {bot.user}')
    print(f'🎵 Using Python with yt-dlp')
    ffmpeg_type = "Local FFmpeg" if "ffmpeg.exe" in FFMPEG_EXECUTABLE else "System FFmpeg"
    print(f'🎵 FFmpeg: {ffmpeg_type} ({FFMPEG_EXECUTABLE})')
    print(f'🎧 Status: Listening to ?help')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.author.send('This command cannot be used in private messages.')
    elif isinstance(error, commands.DisabledCommand):
        await ctx.author.send('Sorry. This command is disabled and cannot be used.')
    elif isinstance(error, commands.CommandInvokeError):
        print(f'In {ctx.command.qualified_name}:')
        print(f'{error.original.__class__.__name__}: {error.original}')

@bot.event
async def on_voice_state_update(member, before, after):
    """Handle auto-disconnect when bot is alone in voice channel"""
    if member.bot:
        return  # Ignore bot voice state changes
    
    # Get the Music cog
    music_cog = bot.get_cog('Music')
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

# Remove default help command to avoid conflicts
bot.remove_command('help')

# Help command
@bot.command(name='help')
async def help_command(ctx):
    """Shows this help message."""
    embed = discord.Embed(
        title="🎵 Music Bot Commands",
        description="Here are all the available commands:",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🎵 **Music Commands**",
        value=f"""
        `{PREFIX}play <song/url/playlist>` - Play music or playlist (⚡ Fast concurrent loading)
        `{PREFIX}pause` - Pause current song
        `{PREFIX}resume` - Resume paused song
        `{PREFIX}skip` - Skip current song
        `{PREFIX}stop` - Stop music and clear queue
        `{PREFIX}queue` - Show music queue
        `{PREFIX}now` - Show currently playing song
        `{PREFIX}volume [1-100]` - Set/check volume
        `{PREFIX}loop` - Toggle loop mode
        `{PREFIX}shuffle` - Shuffle queue
        `{PREFIX}remove <number>` - Remove song from queue
        `{PREFIX}playlist` - Show playlist status
        """,
        inline=False
    )
    
    embed.add_field(
        name="🔧 **Voice Commands**",
        value=f"""
        `{PREFIX}join` - Join your voice channel
        `{PREFIX}leave` - Leave voice channel
        `{PREFIX}summon <channel>` - Join specific channel
        """,
        inline=False
    )
    
    embed.add_field(
        name="🔧 **Troubleshooting**",
        value=f"""
        `{PREFIX}debug` - Show bot status and diagnostics
        `{PREFIX}fix` - Restart audio player if stuck
        """,
        inline=False
    )
    
    embed.add_field(
        name="📝 **Examples**",
        value=f"""
        `{PREFIX}play never gonna give you up`
        `{PREFIX}play https://www.youtube.com/watch?v=...`
        `{PREFIX}play https://www.youtube.com/playlist?list=...` *(⚡ fast-loads)*
        `{PREFIX}play https://music.youtube.com/playlist?list=...` *(⚡ YouTube Music)*
        `{PREFIX}queue 2` *(page 2)* • `{PREFIX}playlist` *(status)*
        `{PREFIX}volume 50` • `{PREFIX}volume` *(check)* • `{PREFIX}skip`
        """,
        inline=False
    )
    
    await ctx.send(embed=embed)

# Run the bot
if __name__ == '__main__':
    bot.run(TOKEN)