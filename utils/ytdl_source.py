"""
YTDL Source class for Discord Music Bot
Handles YouTube-dl operations and audio source management with memory management
"""
import discord
from discord.ext import commands
import yt_dlp
import asyncio
import functools
from config.settings import YDL_OPTIONS, FFMPEG_OPTIONS, FFMPEG_EXECUTABLE
from utils.exceptions import YTDLError
from utils.memory_manager import memory_manager
from utils.cache_manager import cache_manager

class YTDLSource(discord.PCMVolumeTransformer):
    """Audio source using yt-dlp for extraction"""
    YTDL = yt_dlp.YoutubeDL(YDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.5):
        # Handle lazy-loaded sources where source might be None initially
        if source is not None:
            super().__init__(source, volume)
        else:
            # For lazy-loaded sources, we'll set the source later
            self.source = None
            self.volume = volume

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
        
        # Store webpage URL for potential stream refresh
        self.webpage_url = data.get('webpage_url')
        self._ctx = ctx
        
        # Track this audio source for memory management
        memory_manager.track_object(self, 'audio_source')
    
    def __del__(self):
        """Destructor to ensure proper cleanup"""
        try:
            self.cleanup()
        except:
            pass
    
    def cleanup(self):
        """Manually cleanup audio source resources"""
        try:
            # Cleanup audio source
            if hasattr(self, 'source') and self.source:
                if hasattr(self.source, 'cleanup'):
                    self.source.cleanup()
            
            # Clear data references
            if hasattr(self, 'data') and isinstance(self.data, dict):
                self.data.clear()
            
            # Remove from memory tracking
            memory_manager.untrack_object(self)
            
        except Exception as e:
            print(f"⚠️ Error during YTDLSource cleanup: {e}")

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        """Create audio source with full processing and caching"""
        loop = loop or asyncio.get_event_loop()

        print(f"🔍 Creating source for: {search}")
        
        # Check cache first for metadata
        cached_metadata = await cache_manager.get_song_metadata(search)
        if cached_metadata:
            print(f"⚡ Using cached metadata for: {search}")
            
            # Check if we also have cached stream URL
            webpage_url = cached_metadata.get('webpage_url')
            cached_stream = await cache_manager.get_stream_url(webpage_url) if webpage_url else None
            
            if cached_stream:
                print(f"⚡ Using cached stream URL for: {search}")
                # Create source with cached data
                cached_metadata['url'] = cached_stream
                return cls(ctx, discord.FFmpegPCMAudio(cached_stream, **FFMPEG_OPTIONS, executable=FFMPEG_EXECUTABLE), data=cached_metadata)
            else:
                # We have metadata but need fresh stream URL
                print(f"🔄 Refreshing stream URL for cached metadata: {search}")
                try:
                    partial = functools.partial(cls.YTDL.extract_info, webpage_url, download=False)
                    fresh_info = await loop.run_in_executor(None, partial)
                    
                    if fresh_info and 'url' in fresh_info:
                        # Cache the new stream URL
                        await cache_manager.cache_stream_url(webpage_url, fresh_info['url'])
                        
                        # Merge cached metadata with fresh stream URL
                        cached_metadata['url'] = fresh_info['url']
                        return cls(ctx, discord.FFmpegPCMAudio(fresh_info['url'], **FFMPEG_OPTIONS, executable=FFMPEG_EXECUTABLE), data=cached_metadata)
                except Exception as e:
                    print(f"⚠️ Failed to refresh stream URL, falling back to full extraction: {e}")

        # No cache hit, perform full extraction
        print(f"🌐 Full extraction for: {search}")
        
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

        # Cache the extracted data
        try:
            await cache_manager.cache_song_metadata(search, info)
            if 'url' in info:
                await cache_manager.cache_stream_url(webpage_url, info['url'])
            print(f"💾 Cached metadata and stream URL for: {search}")
        except Exception as e:
            print(f"⚠️ Failed to cache data: {e}")

        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **FFMPEG_OPTIONS, executable=FFMPEG_EXECUTABLE), data=info)
        
    @classmethod
    async def create_source_lazy(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        """Create source with metadata only, without extracting stream URL (for playlist loading) with caching"""
        loop = loop or asyncio.get_event_loop()

        # Check cache first for metadata (much faster for playlist loading)
        cached_metadata = await cache_manager.get_song_metadata(search)
        if cached_metadata:
            print(f"⚡ Using cached metadata for lazy load: {search}")
            cached_metadata['_lazy_loaded'] = True
            return cls(ctx, None, data=cached_metadata)

        # No cache hit, extract metadata only (no stream URL processing)
        print(f"🌐 Lazy extraction for: {search}")
        partial = functools.partial(cls.YTDL.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            info = data
        else:
            info = None
            for entry in data['entries']:
                if entry:
                    info = entry
                    break

            if info is None:
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        # Store the webpage URL for later stream extraction
        webpage_url = info.get('webpage_url', search)
        
        # Store the URL for later stream extraction
        info['webpage_url'] = webpage_url
        info['_lazy_loaded'] = True
        
        # Cache the metadata for future use
        try:
            await cache_manager.cache_song_metadata(search, info)
            print(f"💾 Cached lazy metadata for: {search}")
        except Exception as e:
            print(f"⚠️ Failed to cache lazy metadata: {e}")
        
        return cls(ctx, None, data=info)
        
    async def refresh_stream_url(self):
        """Refresh the stream URL if it has expired, or create it for lazy-loaded sources with caching"""
        webpage_url = self.webpage_url or self.url
        if not webpage_url:
            raise YTDLError("No webpage URL available for stream refresh")
            
        try:
            is_lazy = self.data.get('_lazy_loaded', False)
            action = "Creating" if is_lazy else "Refreshing"
            print(f"🔄 {action} stream URL for: {self.title}")
            
            # Check cache first for stream URL
            cached_stream = await cache_manager.get_stream_url(webpage_url)
            if cached_stream:
                print(f"⚡ Using cached stream URL for: {self.title}")
                new_stream_url = cached_stream
            else:
                # No cache hit, extract fresh stream URL
                print(f"🌐 Extracting fresh stream URL for: {self.title}")
                loop = self._ctx.bot.loop
                partial = functools.partial(self.YTDL.extract_info, webpage_url, download=False)
                info = await loop.run_in_executor(None, partial)
                
                if 'entries' not in info:
                    new_stream_url = info['url']
                else:
                    if info['entries'] and info['entries'][0]:
                        new_stream_url = info['entries'][0]['url']
                    else:
                        raise YTDLError("No valid entries found")
                
                # Cache the new stream URL
                await cache_manager.cache_stream_url(webpage_url, new_stream_url)
                print(f"💾 Cached fresh stream URL for: {self.title}")
            
            # Cleanup old audio source before creating new one
            if hasattr(self, 'source') and self.source:
                if hasattr(self.source, 'cleanup'):
                    self.source.cleanup()
            
            # Create new audio source with fresh URL
            new_source = discord.FFmpegPCMAudio(new_stream_url, **FFMPEG_OPTIONS, executable=FFMPEG_EXECUTABLE)
            
            # Update this instance
            if is_lazy and self.source is None:
                # Initialize the parent class for the first time
                super(YTDLSource, self).__init__(new_source, self.volume)
            else:
                # Update existing source
                self.source = new_source
            
            self.stream_url = new_stream_url
            
            # Mark as no longer lazy-loaded
            if is_lazy:
                self.data['_lazy_loaded'] = False
            
            print(f"✅ Stream URL {action.lower()} successful for: {self.title}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to {action.lower()} stream URL for {self.title}: {e}")
            return False
    
    @classmethod
    async def extract_playlist_info(cls, url: str, *, loop: asyncio.BaseEventLoop = None):
        """Extract playlist information without downloading with caching"""
        loop = loop or asyncio.get_event_loop()
        
        print(f"🎵 Extracting playlist info for: {url}")
        
        # Check cache first for playlist data
        cached_playlist = await cache_manager.get_playlist_data(url)
        if cached_playlist:
            print(f"⚡ Using cached playlist data for: {url}")
            return cached_playlist
        
        print(f"🌐 Full playlist extraction for: {url}")
        
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
        
        # Cache the playlist data
        try:
            await cache_manager.cache_playlist_data(url, data)
            print(f"💾 Cached playlist data ({len(valid_entries)} songs) for: {url}")
        except Exception as e:
            print(f"⚠️ Failed to cache playlist data: {e}")
        
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
        """Parse duration from seconds to readable format"""
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