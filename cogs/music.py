"""
Music Cog for Discord Music Bot
Contains all music-related commands and functionality
"""
import discord
from discord.ext import commands
import asyncio
import math

from utils.voice_state import VoiceState
from utils.ytdl_source import YTDLSource
from utils.song import Song
from utils.exceptions import VoiceError, YTDLError
from utils.error_handler import error_handler
from utils.database_manager import database_manager
from utils.ui_enhancements import (
    LoadingIndicator, EnhancedEmbed, SmartPlaybackFeedback,
    InteractionEnhancer, ProgressBar, format_duration
)
from config.settings import PREFIX

class Music(commands.Cog):
    """Music cog with voice playback functionality"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    async def _maybe_defer(self, ctx: commands.Context):
        """Defer interaction response for slash-invoked hybrid commands to avoid 404 Unknown interaction."""
        try:
            interaction = getattr(ctx, "interaction", None)
            if interaction and not interaction.response.is_done():
                await interaction.response.defer()
        except Exception:
            pass

    def get_voice_state(self, ctx: commands.Context):
        """Get or create voice state for a guild"""
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        """Check if command can be used (no DMs)"""
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        """Set up voice state before each command"""
        await self._maybe_defer(ctx)
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle cog-specific errors using centralized error handler"""
        await error_handler.handle_error(error, ctx, "Music Cog Error")

    @commands.hybrid_command(name='join', invoke_without_subcommand=True, description='Join your voice channel')
    async def _join(self, ctx: commands.Context):
        """Joins a voice channel."""

        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()
        
        # Restart audio player task now that we have a voice connection
        await ctx.voice_state._restart_audio_player_if_needed()

    @commands.hybrid_command(name='summon', description='Summon the bot to a specific voice channel')
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
        
        # Restart audio player task now that we have a voice connection
        await ctx.voice_state._restart_audio_player_if_needed()

    @commands.hybrid_command(name='leave', aliases=['disconnect'], description='Leave voice channel and clear the queue')
    @commands.has_permissions(manage_guild=True)
    async def _leave(self, ctx: commands.Context):
        """Clears the queue and leaves the voice channel."""

        if not ctx.voice_state.voice:
            return await ctx.send('Not connected to any voice channel.')

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]

    @commands.hybrid_command(name='volume', aliases=['vol'], description='Set or check the volume (1-100)')
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

    @commands.hybrid_command(name='now', aliases=['current', 'playing'], description='Show the currently playing song')
    async def _now(self, ctx: commands.Context):
        """Displays the currently playing song with enhanced details."""
        
        if not ctx.voice_state.current:
            embed = EnhancedEmbed.create_music_embed(
                "No Music Playing", 
                "📭 Nothing is currently playing.\nUse `?play <song>` to start playing music!",
                discord.Color.orange()
            )
            return await ctx.send(embed=embed)
        
        # Create song info dict  
        current_song = ctx.voice_state.current.source
        song_info = {
            'title': current_song.title,
            'uploader': current_song.uploader,
            'duration': getattr(current_song, 'duration', 0),
            'thumbnail': getattr(current_song, 'thumbnail', None),
            'webpage_url': getattr(current_song, 'webpage_url', None)
        }
        
        # Create enhanced now playing embed
        embed = EnhancedEmbed.create_now_playing_embed(song_info, ctx.voice_state)
        
        # Add additional playback info
        if ctx.voice_state.loop:
            embed.add_field(
                name="🔁 Loop Mode",
                value="Current song will repeat",
                inline=True
            )
        
        # Add requester info if available
        if hasattr(ctx.voice_state.current, 'requester'):
            embed.add_field(
                name="👤 Requested by",
                value=ctx.voice_state.current.requester.mention,
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='pause', description='Pause the currently playing song')
    @commands.has_permissions(manage_guild=True)
    async def _pause(self, ctx: commands.Context):
        """Pauses the currently playing song."""

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            await ctx.send('⏸️ Paused')

    @commands.hybrid_command(name='resume', description='Resume the paused song')
    @commands.has_permissions(manage_guild=True)
    async def _resume(self, ctx: commands.Context):
        """Resumes a currently paused song."""

        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            await ctx.send('▶️ Resumed')

    @commands.hybrid_command(name='stop', description='Stop playback and clear the queue')
    @commands.has_permissions(manage_guild=True)
    async def _stop(self, ctx: commands.Context):
        """Stops playing song and clears the queue."""

        ctx.voice_state.songs.clear()
        await ctx.voice_state.clear_playlist()  # Clear current playlist and remove from cache

        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.stop()
            
        await ctx.send('⏹️ Stopped and cleared queue')

    @commands.hybrid_command(name='skip', description='Vote to skip the current song')
    async def _skip(self, ctx: commands.Context):
        """Vote to skip a song. The requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        if not ctx.voice_state.is_playing:
            return await ctx.send('Not playing any music right now...')

        voter = ctx.message.author
        if voter == ctx.voice_state.current.requester:
            await ctx.send('⏭️ Skipped')
            ctx.voice_state.skip()

        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            total_votes = len(ctx.voice_state.skip_votes)

            if total_votes >= 3:
                await ctx.send('⏭️ Skipped by vote')
                ctx.voice_state.skip()
            else:
                await ctx.send('Skip vote added, currently **{}/3**'.format(total_votes))

        else:
            await ctx.send('You have already voted to skip this song.')

    @commands.hybrid_command(name='queue', aliases=['q'], description='Show the music queue (paginated)')
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

        # Validate page number
        if page < 1:
            page = 1
        elif page > pages:
            return await ctx.send(f'📋 **Page {page} not found!**\n'
                                f'Queue only has **{pages} page(s)**. Use `?queue {pages}` for the last page.')

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

        # Create more informative description
        total_songs = len(ctx.voice_state.songs)
        
        if pages == 1:
            # Single page - no need for pagination info
            description = f'**{total_songs} tracks in queue:**\n\n{queue}{playlist_info}'
            footer_text = f'{total_songs} songs total'
        else:
            # Multiple pages - show pagination info
            showing_start = start + 1
            showing_end = min(end, total_songs)
            description = f'**{total_songs} tracks in queue** (showing {showing_start}-{showing_end}):\n\n{queue}{playlist_info}'
            footer_text = 'Page {}/{} • Use /queue page:<n> to navigate'.format(page, pages)
        
        embed = (discord.Embed(
            title="📋 Music Queue", 
            description=description,
            color=discord.Color.blue()
        ).set_footer(text=footer_text))
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='shuffle', description='Shuffle the current queue')
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
                await ctx.send('🔀 Shuffled')
        else:
            await ctx.send('🔀 Shuffled')

    @commands.hybrid_command(name='remove', description='Remove a song from the queue by number')
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a song from the queue at a given index."""

        if len(ctx.voice_state.songs) == 0:
            return await ctx.send('Empty queue.')

        ctx.voice_state.songs.remove(index - 1)
        await ctx.send(f'✅ Removed song #{index}')

    @commands.hybrid_command(name='loop', description='Toggle loop for the current song')
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
    
    @commands.hybrid_command(name='playlist', aliases=['pl'], description='Show current playlist status')
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

    @commands.hybrid_command(name='debug', aliases=['debug_status', 'voice_debug'], description='Show bot voice/debug information')
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
        needs_restart = False
        if hasattr(voice_state, 'audio_player') and voice_state.audio_player:
            if voice_state.audio_player.done():
                player_status = "💀 Crashed/Stopped"
                needs_restart = True
            elif voice_state.audio_player.cancelled():
                player_status = "⏹️ Cancelled"
                needs_restart = True
            else:
                player_status = "✅ Running"
        else:
            needs_restart = True
        
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
        
        # Playlist Status (if active)
        if voice_state.current_playlist:
            playlist_title = voice_state.current_playlist.get('title', 'Unknown')[:30]
            total_songs = len(voice_state.current_playlist['entries'])
            remaining = total_songs - voice_state.playlist_position
            embed.add_field(
                name="📀 Active Playlist",
                value=f"🎵 {playlist_title}...\n📊 {remaining}/{total_songs} remaining",
                inline=False
            )
        
        # Hosting Environment Info
        import platform
        from config.settings import FFMPEG_EXECUTABLE
        hosting_info = f"🖥️ {platform.system()} {platform.release()}"
        if FFMPEG_EXECUTABLE:
            ffmpeg_type = "Local" if "ffmpeg.exe" in FFMPEG_EXECUTABLE else "System"
            hosting_info += f"\n🎬 FFmpeg: {ffmpeg_type}"
        
        embed.add_field(
            name="🌐 Environment",
            value=hosting_info,
            inline=True
        )
        
        # Set footer with context-aware message
        footer_text = "Enhanced for hosting stability"
        if needs_restart and len(voice_state.songs) > 0:
            footer_text = "⚠️ Audio player needs restart • Use ?fix • " + footer_text
        elif not needs_restart:
            footer_text = "✅ All systems running • " + footer_text
        else:
            footer_text = "Use ?fix if audio player is stuck • " + footer_text
            
        embed.set_footer(text=footer_text)
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='fix', aliases=['restart'], description='Attempt to fix/restart the audio player')
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
            embed.add_field(name="📝 Result", value="Audio player restarted, but queue is empty. Add songs with `/play`", inline=False)
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='play', aliases=['p'], description='Play a song or playlist by name or URL')
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

        # If invoked as a slash command, defer to avoid interaction timeout
        try:
            if getattr(ctx, "interaction", None):
                await ctx.defer()
        except Exception:
            pass

        async with ctx.typing():
            # Check for unsupported URLs first
            if search.startswith(('http://', 'https://')):
                is_unsupported, error_msg = self._is_unsupported_url(search)
                if is_unsupported:
                    await ctx.send(error_msg)
                    return
            
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
            
            # Single song handling with enhanced UI feedback
            loading = LoadingIndicator(ctx, "🔍 Searching for song...")
            
            try:
                # Start loading animation
                await loading.start(animation_type='music', update_interval=0.8)
                
                # Update loading stages
                await loading.update_stage(0)  # Searching
                await asyncio.sleep(0.5)
                
                await loading.update_stage(1)  # Connecting
                source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop)
                
                await loading.update_stage(2)  # Extracting
                song = Song(source)
                
                await loading.update_stage(3)  # Preparing
                await ctx.voice_state.songs.put(song)
                
                # Stop loading and show final result
                queue_position = len(ctx.voice_state.songs)
                is_playing_now = queue_position <= 1 and not ctx.voice_state.is_playing
                
                await loading.stop(
                    final_message="✅ Song added successfully!",
                    final_color=discord.Color.green()
                )
                
                # Send enhanced feedback
                song_info = {
                    'title': source.title,
                    'uploader': source.uploader,
                    'duration': source.duration,
                    'thumbnail': getattr(source, 'thumbnail', None),
                    'webpage_url': getattr(source, 'webpage_url', None)
                }
                
                await SmartPlaybackFeedback.send_song_added_feedback(
                    ctx, song_info, queue_position, is_playing_now
                )
                
                # Track user activity in database
                await database_manager.track_user_activity(
                    ctx.author.id, ctx.guild.id, str(ctx.author), 'song_queued',
                    {'song_title': source.title, 'search_query': search}
                )
                
                # Initialize guild settings if not exists
                guild_settings = await database_manager.get_guild_settings(ctx.guild.id, ctx.guild.name)
                
            except (YTDLError, Exception) as e:
                # Stop loading with error
                await loading.stop(
                    final_message="❌ Failed to add song",
                    final_color=discord.Color.red()
                )
                
                # Use centralized error handler for better user experience
                await error_handler.handle_error(e, ctx, f"Failed to process: {search}")
    
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
        
        # Note: Audio player task is already created in VoiceState.__init__()
        # and should automatically start playing when songs are added to the queue.
        # No need to restart it here - that was causing double playback issues.
    
    def _is_unsupported_url(self, url: str) -> tuple[bool, str]:
        """Check if URL is from an unsupported service and return helpful message"""
        url_lower = url.lower()
        
        # DRM-protected music services
        if 'open.spotify.com' in url_lower or 'spotify.com' in url_lower:
            return True, "🚫 **Spotify is not supported** due to DRM protection.\n\n✅ **Alternatives:**\n• Copy song name: `?play [song name] [artist]`\n• Use YouTube Music: `?play [song name / playlist link]`\n• Example: `?play bad habits ed sheeran`"
            
        elif 'music.apple.com' in url_lower or 'itunes.apple.com' in url_lower:
            return True, "🚫 **Apple Music is not supported** due to DRM protection.\n\n✅ **Alternatives:**\n• Copy song name: `?play [song name] [artist]`\n• Use YouTube Music: `?play [song name / playlist link]`"
            
        elif 'tidal.com' in url_lower:
            return True, "🚫 **Tidal is not supported** due to DRM protection.\n\n✅ **Alternatives:**\n• Copy song name: `?play [song name] [artist]`\n• Use YouTube Music: `?play [song name / playlist link]`"
            
        elif 'deezer.com' in url_lower:
            return True, "🚫 **Deezer is not supported** due to DRM protection.\n\n✅ **Alternatives:**\n• Copy song name: `?play [song name] [artist]`\n• Use YouTube Music: `?play [song name / playlist link]`"
            
        elif 'music.amazon.com' in url_lower or 'amazon.com/music' in url_lower:
            return True, "🚫 **Amazon Music is not supported** due to DRM protection.\n\n✅ **Alternatives:**\n• Copy song name: `?play [song name] [artist]`\n• Use YouTube Music: `?play [song name / playlist link]`"
            
        # Other potentially problematic services
        elif 'netflix.com' in url_lower:
            return True, "🚫 **Netflix is not supported** - this is a video streaming service.\n\n✅ **This bot is for music/audio:**\n• YouTube: `?play [song/video]`\n• SoundCloud: `?play [soundcloud link]`"
            
        elif 'hulu.com' in url_lower or 'disney' in url_lower:
            return True, "🚫 **Video streaming services are not supported**.\n\n✅ **This bot is for music/audio:**\n• YouTube: `?play [song/video]`\n• SoundCloud: `?play [soundcloud link]`"
            
        return False, ""

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
        """Ensure user is in voice channel before music commands"""
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Bot is already in a voice channel.')

    @commands.hybrid_command(name='clear_playlist_cache', aliases=['clearplcache', 'resetplcache'], description='Clear playlist cache to resolve issues')
    @commands.has_permissions(manage_guild=True)
    async def _clear_playlist_cache(self, ctx: commands.Context):
        """Clear playlist cache to fix stuck playlist issues (Manage Server permission required)."""
        try:
            from utils.cache_manager import cache_manager
            
            # Get stats before clearing
            cache_entries = len(cache_manager.playlist_cache.cache)
            
            # Clear playlist cache
            cache_manager.playlist_cache.clear()
            
            # Clear current playlist state
            await ctx.voice_state.clear_playlist()
            
            embed = discord.Embed(
                title="🧹 Playlist Cache Cleared",
                description="Playlist cache has been reset to fix stuck playlist issues",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="📊 Cleared Data",
                value=f"**Playlist Cache Entries:** {cache_entries}\n"
                      f"**Current Playlist State:** Cleared",
                inline=False
            )
            
            embed.add_field(
                name="✅ What This Fixes",
                value="• Stuck on old playlist after ?stop\n"
                      "• Wrong playlist name showing\n"
                      "• Playlist switching issues",
                inline=False
            )
            
            embed.set_footer(text="Try loading your playlist again after this command")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error clearing playlist cache: {str(e)}")

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(Music(bot))