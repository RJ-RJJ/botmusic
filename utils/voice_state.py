"""
VoiceState class for Discord Music Bot
Manages voice connection, queue, and playback state for each guild with memory management
"""
import asyncio
from discord.ext import commands
import discord
from utils.song_queue import SongQueue
from utils.song import Song
from utils.ytdl_source import YTDLSource
from utils.memory_manager import memory_manager
from config.settings import (
    PLAYLIST_BATCH_SIZE, 
    PLAYLIST_LOW_THRESHOLD, 
    CONCURRENT_LOAD_LIMIT,
    AUTO_DISCONNECT_DELAY,
    FFMPEG_OPTIONS,
    FFMPEG_EXECUTABLE
)

class VoiceState:
    """Manages voice connection and playback state for a guild"""
    
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
        self.playlist_batch_size = PLAYLIST_BATCH_SIZE
        self.playlist_low_threshold = PLAYLIST_LOW_THRESHOLD
        self.concurrent_load_limit = CONCURRENT_LOAD_LIMIT
        self._background_loading = False  # Flag to prevent multiple background loads

        self.audio_player = bot.loop.create_task(self.audio_player_task())
        
        # Track voice state for memory management
        memory_manager.track_object(self, 'voice_state')

    def __del__(self):
        """Destructor with proper cleanup"""
        try:
            if hasattr(self, 'audio_player') and self.audio_player:
                self.audio_player.cancel()
            self.cleanup_resources()
        except:
            pass
    
    def cleanup_resources(self):
        """Manual cleanup of resources"""
        try:
            # Cleanup current song
            if self.current and hasattr(self.current, 'source'):
                if hasattr(self.current.source, 'cleanup'):
                    self.current.source.cleanup()
            
            # Cleanup songs in queue
            while not self.songs.empty():
                try:
                    song = self.songs.get_nowait()
                    if hasattr(song, 'source') and hasattr(song.source, 'cleanup'):
                        song.source.cleanup()
                except:
                    break
            
            # Clear playlist data
            if self.current_playlist and isinstance(self.current_playlist, dict):
                self.current_playlist.clear()
            
            # Remove from memory tracking
            memory_manager.untrack_object(self)
            
        except Exception as e:
            print(f"⚠️ Error during VoiceState cleanup: {e}")

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
                
                # Check if this is a lazy-loaded source that needs stream URL extraction
                if hasattr(self.current.source, 'data') and self.current.source.data.get('_lazy_loaded'):
                    print(f"🔄 Lazy-loaded source detected, extracting fresh stream URL for: {self.current.source.title}")
                    if not await self.current.source.refresh_stream_url():
                        print(f"❌ Failed to extract stream URL for lazy-loaded source: {self.current.source.title}")
                        # Skip to next song
                        self.next.set()
                        continue
                
                # Try to play, with stream refresh retry if it fails
                play_success = False
                for attempt in range(2):  # Try original, then retry with refresh
                    try:
                        self.voice.play(self.current.source, after=self.play_next_song)
                        play_success = True
                        break
                    except Exception as e:
                        error_str = str(e).lower()
                        if attempt == 0 and any(keyword in error_str for keyword in ['403', 'forbidden', 'expired', 'unavailable']):
                            print(f"⚠️ Stream error on attempt {attempt + 1}, trying to refresh URL: {e}")
                            # Try to refresh the stream URL
                            if await self.current.source.refresh_stream_url():
                                continue  # Retry with refreshed URL
                        
                        # If we get here, either it's not a stream error or refresh failed
                        print(f"❌ Playback failed after {attempt + 1} attempts: {e}")
                        if attempt == 1:  # Last attempt failed
                            raise e
                
                if not play_success:
                    print(f"❌ Failed to start playback for: {self.current.source.title}")
                    # Skip to next song
                    self.next.set()
                    continue
                
                # Brief delay to allow audio to start properly
                await asyncio.sleep(0.1)
                
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
        """Callback for when a song finishes playing"""
        current_song = getattr(self.current, 'source', {})
        song_title = getattr(current_song, 'title', 'Unknown Song')
        
        if error:
            # Handle common FFmpeg errors more gracefully
            error_str = str(error)
            if "'_MissingSentinel' object has no attribute 'read'" in error_str:
                print(f"🔧 FFmpeg audio source error for '{song_title}' - likely due to stream expiration during loop")
                # Don't raise the error, just continue to next song
                self.loop = False  # Disable loop to prevent repeated errors
            elif any(keyword in error_str.lower() for keyword in ['403', 'forbidden', 'expired', 'unavailable']):
                print(f"🔄 Stream URL expired during playback for '{song_title}': {error_str}")
                # These indicate stream URL expiration - future songs should refresh their URLs
            elif any(keyword in error_str.lower() for keyword in ['ffmpeg', 'audio', 'network', 'connection', 'timeout', 'http']):
                print(f"🌐 Network/Audio playback error for '{song_title}' (recovered): {error_str}")
                # Don't crash the bot for network issues, just continue
            elif "keepalive request failed" in error_str or "Cannot reuse HTTP connection" in error_str:
                print(f"🔄 YouTube CDN switching error for '{song_title}' (normal for hosting): {error_str}")
                # These are expected on hosting platforms, don't crash
            else:
                # For other unexpected errors, still log them but don't crash
                print(f"⚠️ Unexpected playback error for '{song_title}' (continuing): {error_str}")
                # Changed from raising error to logging - better for stability
        else:
            print(f"✅ Song '{song_title}' finished normally, moving to next")

        self.next.set()

    def skip(self):
        """Skip the current song"""
        self.skip_votes.clear()

        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        """Stop playback and clear queue with proper cleanup"""
        # Cleanup current song
        if self.current and hasattr(self.current, 'source'):
            if hasattr(self.current.source, 'cleanup'):
                self.current.source.cleanup()
        
        # Cleanup all songs in queue
        while not self.songs.empty():
            try:
                song = self.songs.get_nowait()
                if hasattr(song, 'source') and hasattr(song.source, 'cleanup'):
                    song.source.cleanup()
            except:
                break
        
        self.songs.clear()
        
        # Cancel disconnect timer if it exists
        if self.disconnect_timer:
            self.disconnect_timer.cancel()
            self.disconnect_timer = None

        # Cleanup voice connection
        if self.voice:
            # Track voice connection for cleanup
            await memory_manager.cleanup_voice_connection(self.voice)
            self.voice = None
        
        # Manual cleanup of resources
        self.cleanup_resources()
    
    def start_disconnect_timer(self):
        """Start a timer to disconnect if bot is alone for too long"""
        if self.disconnect_timer:
            self.disconnect_timer.cancel()
        
        # Disconnect after configured delay
        self.disconnect_timer = self.bot.loop.create_task(self._disconnect_after_delay())
    
    def cancel_disconnect_timer(self):
        """Cancel the disconnect timer when users rejoin"""
        if self.disconnect_timer:
            self.disconnect_timer.cancel()
            self.disconnect_timer = None
    
    async def _disconnect_after_delay(self):
        """Internal method to handle delayed disconnection"""
        try:
            await asyncio.sleep(AUTO_DISCONNECT_DELAY)
            
            # Double-check that bot is still alone before disconnecting
            if self.voice and len(self.voice.channel.members) == 1:  # Only bot in channel
                await self._ctx.send(f"🔌 Left voice channel due to inactivity ({AUTO_DISCONNECT_DELAY//60} minutes alone)")
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
            # For playlist songs, use lightweight loading (metadata only)
            source = await YTDLSource.create_source_lazy(self._ctx, url, loop=self.bot.loop)
            return Song(source)
        except Exception as e:
            # Re-raise the exception to be handled by the caller
            raise e
    
    async def _restart_audio_player_if_needed(self):
        """Restart audio player task if it's not running (called after voice connection established)"""
        # Check if audio player task exists and is healthy
        if hasattr(self, 'audio_player') and self.audio_player:
            if not self.audio_player.done() and not self.audio_player.cancelled():
                # Audio player is running fine
                print("🎵 Audio player already running - no restart needed")
                return
        
        # Audio player is not running or has crashed, restart it
        print("🔧 Restarting audio player after voice connection established")
        
        # Cancel old task if it exists
        if hasattr(self, 'audio_player') and self.audio_player:
            self.audio_player.cancel()
            await asyncio.sleep(0.1)  # Brief delay to ensure cancellation
        
        # Create new audio player task
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())
    
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
    
    async def clear_playlist(self):
        """Clear the current playlist and remove from cache"""
        # If we have a current playlist, delete it from cache
        if self.current_playlist and 'webpage_url' in self.current_playlist:
            try:
                # Import cache_manager if not already imported
                from utils.cache_manager import cache_manager
                
                # Get the playlist URL
                playlist_url = self.current_playlist.get('webpage_url')
                if playlist_url:
                    # Generate the cache key
                    normalized_url = cache_manager._normalize_url(playlist_url)
                    key = cache_manager._generate_key("playlist", normalized_url)
                    
                    # Delete from playlist cache
                    cache_manager.playlist_cache.delete(key)
                    print(f"🧹 Removed playlist from cache: {playlist_url}")
            except Exception as e:
                print(f"⚠️ Error removing playlist from cache: {e}")
        
        # Clear playlist data
        self.current_playlist = None
        self.playlist_position = 0