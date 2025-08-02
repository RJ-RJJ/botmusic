"""
Info Cog for Discord Music Bot
Contains help, stats, and platform information commands
"""
import discord
from discord.ext import commands
import platform
from config.settings import PREFIX
from utils.helpers import get_server_count, get_simple_status_messages
from utils.memory_manager import memory_manager
from utils.error_handler import error_handler
from utils.cache_manager import cache_manager

class Info(commands.Cog):
    """Information and help commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='help')
    async def help_command(self, ctx):
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
            name="🔧 **Troubleshooting & Info**",
            value=f"""
    `{PREFIX}stats` - Show bot statistics & status
    `{PREFIX}debug` - Show bot status and diagnostics
    `{PREFIX}fix` - Restart audio player if stuck
    `{PREFIX}platforms` - Show supported platforms & alternatives
    `{PREFIX}memory` - Show memory usage (Admin)
    `{PREFIX}cleanup` - Force memory cleanup (Admin)
    `{PREFIX}errors` - Show error statistics (Admin)
    `{PREFIX}cache` - Show cache statistics (Admin)
    `{PREFIX}cache_clear` - Clear all caches (Admin)
            """,
            inline=False
        )
        
        embed.add_field(
            name="✅ **Supported Platforms**",
            value="""
    **✅ Supported:** YouTube, YouTube Music, SoundCloud, Bandcamp, Vimeo, TikTok
    **❌ Not Supported:** Spotify, Apple Music, Tidal, Deezer (DRM protected)

    *For unsupported platforms: copy song name and search instead!*
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

    @commands.command(name='stats', aliases=['statistics', 'info'])
    async def stats_command(self, ctx):
        """Shows simple bot statistics and current status."""
        embed = discord.Embed(
            title="📊 Bot Statistics",
            description="Here are the current bot stats:",
            color=discord.Color.purple()
        )
        
        # Basic stats
        server_count = get_server_count()
        
        embed.add_field(
            name="🌐 Server Info",
            value=f"**Servers:** {server_count}\n**Prefix:** `{PREFIX}`\n**Commands:** {len(self.bot.commands)}",
            inline=True
        )
        
        # Current activity
        music_cog = self.bot.get_cog('Music')
        active_guilds = 0
        total_queue = 0
        if music_cog:
            for voice_state in music_cog.voice_states.values():
                if voice_state.is_playing:
                    active_guilds += 1
                total_queue += len(voice_state.songs)
        
        embed.add_field(
            name="🎧 Current Activity",
            value=f"**Active Music:** {active_guilds} servers\n**Total Queue:** {total_queue} songs\n**Bot Status:** Online ✅",
            inline=True
        )
        
        # Performance info
        embed.add_field(
            name="⚡ Performance",
            value=f"**Platform:** {platform.system()}\n**Python:** {platform.python_version()}\n**Discord.py:** {discord.__version__}",
            inline=True
        )
        
        # Cool features
        embed.add_field(
            name="🚀 Features",
            value="**⚡ Fast Playlist Loading**\n**🎵 Auto Queue**\n**🔄 Background Loading**\n**📱 Multi-Platform Support**",
            inline=True
        )
        
        # Simple Status Info
        status_messages = get_simple_status_messages()
        embed.add_field(
            name="🎪 Status Rotation",
            value=f"**Mode:** Simple 3-status rotation\n**Messages:** {len(status_messages)}\n\n**Preview:**\n• Listening to {status_messages[0]}\n• Watching {status_messages[1]}\n• Playing: {status_messages[2]}",
            inline=False
        )
        
        embed.set_footer(text=f"Use {PREFIX}help for commands")
        
        await ctx.send(embed=embed)

    @commands.command(name='platforms', aliases=['sites', 'support'])
    async def supported_platforms(self, ctx):
        """Shows detailed information about supported platforms."""
        embed = discord.Embed(
            title="🌐 Supported Audio Platforms",
            description="Berikut platform yang didukung dan tidak didukung oleh bot:",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="✅ **DIDUKUNG (Gratis)**",
            value="""
    **🎵 Music Platforms:**
    • **YouTube** - Semua video/musik
    • **YouTube Music** - Playlist & single songs
    • **SoundCloud** - Public tracks
    • **Bandcamp** - Free tracks
    • **Vimeo** - Audio/video content

    **📱 Social Media:**
    • **TikTok** - Public videos
    • **Twitter/X** - Video dengan audio
    • **Facebook** - Public videos

    **📻 Other:**
    • **Internet Radio** - Stream URLs
    • **Mixcloud** - DJ sets & radio shows
            """,
            inline=True
        )
        
        embed.add_field(
            name="❌ **TIDAK DIDUKUNG**",
            value="""
    **🔒 DRM-Protected Services:**
    • **Spotify** - Premium & DRM
    • **Apple Music** - DRM protected  
    • **Tidal** - High-quality DRM
    • **Deezer** - Subscription service
    • **Amazon Music** - DRM protected
    • **YouTube Music Premium** - DRM tracks

    **📺 Video Streaming:**
    • **Netflix** - DRM protected
    • **Disney+** - DRM protected
    • **Hulu** - DRM protected

    **💡 Alasan:** DRM encryption mencegah ekstraksi audio
            """,
            inline=True
        )
        
        embed.add_field(
            name="🔄 **Cara Menggunakan Platform Tidak Didukung**",
            value=f"""
    **Step 1:** Copy nama lagu dari platform yang tidak didukung
    **Step 2:** Search di YouTube dengan bot:

    **Contoh:**
    ```
    Spotify: "Bad Habits - Ed Sheeran"
    Bot: {PREFIX}play bad habits ed sheeran
    ```

    **Untuk Playlist:**
    1. Buat playlist di YouTube Music
    2. Copy playlist URL ke bot
    3. `{PREFIX}play https://music.youtube.com/playlist?list=...`
            """,
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='memory', aliases=['mem', 'ram'])
    @commands.has_permissions(manage_guild=True)
    async def memory_stats(self, ctx):
        """Shows memory usage and management statistics."""
        embed = discord.Embed(
            title="🧠 Memory Management",
            description="Current memory usage and tracking statistics:",
            color=discord.Color.orange()
        )
        
        # Get memory stats
        stats = memory_manager.get_memory_stats()
        
        if 'error' in stats:
            embed.add_field(
                name="❌ Error",
                value="Could not retrieve memory statistics",
                inline=False
            )
        else:
            embed.add_field(
                name="📊 Memory Usage",
                value=f"**RSS:** {stats['rss_mb']:.1f} MB\n"
                      f"**VMS:** {stats['vms_mb']:.1f} MB\n"
                      f"**Percent:** {stats['percent']:.1f}%",
                inline=True
            )
            
            embed.add_field(
                name="🎵 Tracked Objects",
                value=f"**Total:** {stats['tracked_objects']}\n"
                      f"**Audio Sources:** {stats['audio_sources']}\n"
                      f"**Voice Connections:** {stats['voice_connections']}\n"
                      f"**YTDL Instances:** {stats['ytdl_instances']}",
                inline=True
            )
            
            embed.add_field(
                name="🧹 Cleanup Stats",
                value=f"**Total Freed:** {stats['total_freed_mb']:.1f} MB\n"
                      f"**Last Cleanup:** {stats['last_cleanup'].strftime('%H:%M:%S') if stats['last_cleanup'] else 'Never'}",
                inline=True
            )
        
        # Add music-specific stats
        music_cog = self.bot.get_cog('Music')
        if music_cog:
            active_voices = len([vs for vs in music_cog.voice_states.values() if vs.voice and vs.voice.is_connected()])
            total_queue_songs = sum(len(vs.songs) for vs in music_cog.voice_states.values())
            
            embed.add_field(
                name="🎵 Music State",
                value=f"**Active Voices:** {active_voices}\n"
                      f"**Queued Songs:** {total_queue_songs}\n"
                      f"**Voice States:** {len(music_cog.voice_states)}",
                inline=False
            )
        
        embed.set_footer(text="Use ?cleanup to force memory cleanup")
        await ctx.send(embed=embed)

    @commands.command(name='cleanup')
    @commands.has_permissions(manage_guild=True)
    async def force_cleanup(self, ctx):
        """Force memory cleanup and garbage collection."""
        async with ctx.typing():
            before_stats = memory_manager.get_memory_stats()
            before_memory = before_stats.get('rss_mb', 0)
            before_objects = before_stats.get('tracked_objects', 0)
            
            # Force cleanup
            freed_mb = await memory_manager.force_garbage_collection()
            
            after_stats = memory_manager.get_memory_stats()
            after_memory = after_stats.get('rss_mb', 0)
            after_objects = after_stats.get('tracked_objects', 0)
            
            cleaned_objects = before_objects - after_objects
        
        embed = discord.Embed(
            title="🧹 Memory Cleanup Complete",
            description="Forced garbage collection and memory cleanup",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Memory Change",
            value=f"**Before:** {before_memory:.1f} MB\n"
                  f"**After:** {after_memory:.1f} MB\n"
                  f"**Freed:** {freed_mb:.1f} MB",
            inline=True
        )
        
        embed.add_field(
            name="🗑️ Objects Cleaned",
            value=f"**Before:** {before_objects}\n"
                  f"**After:** {after_objects}\n"
                  f"**Cleaned:** {cleaned_objects}",
            inline=True
        )
        
        if freed_mb > 1.0 or cleaned_objects > 0:
            embed.color = discord.Color.green()
            embed.add_field(
                name="✅ Result",
                value="Cleanup was effective!",
                inline=False
            )
        else:
            embed.color = discord.Color.blue()
            embed.add_field(
                name="ℹ️ Result", 
                value="System was already clean",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='errors', aliases=['error_stats', 'errstats'])
    @commands.has_permissions(manage_guild=True)
    async def error_statistics(self, ctx):
        """Shows error statistics and most common errors."""
        stats = error_handler.get_error_statistics()
        
        embed = discord.Embed(
            title="🚨 Error Statistics",
            description="Error tracking and analysis:",
            color=discord.Color.red()
        )
        
        # Total errors
        embed.add_field(
            name="📊 Overview",
            value=f"**Total Errors:** {stats['total_errors']}\n"
                  f"**Categories:** {len(stats['by_category'])}",
            inline=True
        )
        
        # Errors by category
        if stats['by_category']:
            category_text = ""
            for category, errors in stats['by_category'].items():
                total = sum(errors.values())
                category_name = category.replace('_', ' ').title()
                category_text += f"• **{category_name}:** {total}\n"
            
            embed.add_field(
                name="📂 By Category",
                value=category_text[:1024] if category_text else "No errors recorded",
                inline=True
            )
        
        # Most common errors
        if stats['most_common']:
            common_errors = ""
            for i, error in enumerate(stats['most_common'][:5], 1):
                category_name = error['category'].replace('_', ' ').title()
                common_errors += f"{i}. **{error['type']}** ({category_name}): {error['count']}\n"
            
            embed.add_field(
                name="🔥 Most Common",
                value=common_errors,
                inline=False
            )
        else:
            embed.add_field(
                name="🎉 Status",
                value="No errors recorded yet!",
                inline=False
            )
        
        embed.set_footer(text="Use ?cleanup to clear error logs")
        await ctx.send(embed=embed)

    @commands.command(name='test_error', aliases=['testerr'])
    @commands.has_permissions(administrator=True)
    async def test_error_handling(self, ctx, error_type: str = "user"):
        """Test the error handling system (Admin only)."""
        
        if error_type.lower() == "user":
            # Simulate user error
            raise commands.MissingRequiredArgument(commands.Parameter("test_param", commands.Parameter.POSITIONAL_OR_KEYWORD))
        elif error_type.lower() == "voice":
            # Simulate voice error
            from utils.exceptions import VoiceError
            raise VoiceError("Test voice connection error")
        elif error_type.lower() == "music":
            # Simulate music error
            from utils.exceptions import YTDLError
            raise YTDLError("Test music loading error")
        elif error_type.lower() == "permission":
            # Simulate permission error
            raise commands.MissingPermissions(["manage_messages"])
        elif error_type.lower() == "system":
            # Simulate system error
            raise RuntimeError("Test system error")
        else:
            await ctx.send("Available test types: `user`, `voice`, `music`, `permission`, `system`")

    @commands.command(name='cache', aliases=['cache_stats', 'cacheinfo'])
    @commands.has_permissions(manage_guild=True)
    async def cache_statistics(self, ctx):
        """Shows cache statistics and performance metrics."""
        stats = cache_manager.get_comprehensive_stats()
        efficiency = cache_manager.get_cache_efficiency_report()
        
        embed = discord.Embed(
            title="⚡ Cache Statistics",
            description="Cache performance and efficiency metrics:",
            color=discord.Color.gold()
        )
        
        # Overview
        embed.add_field(
            name="📊 Overview",
            value=f"**Total Entries:** {stats['total_entries']}\n"
                  f"**Uptime:** {stats['uptime_formatted']}\n"
                  f"**Overall Hit Rate:** {efficiency['overall_hit_rate']}%",
            inline=True
        )
        
        # Cache Performance
        embed.add_field(
            name="🚀 Performance",
            value=f"**Speed Improvement:** {efficiency['performance_improvement']}\n"
                  f"**API Calls Saved:** {efficiency['api_calls_saved']}\n"
                  f"**Memory Saved:** {efficiency['memory_saved_estimate']}",
            inline=True
        )
        
        # Individual Cache Stats
        cache_details = ""
        caches = [
            ("🎵 Metadata", stats['metadata_cache']),
            ("🔗 Stream URLs", stats['stream_cache']),
            ("📀 Playlists", stats['playlist_cache']),
            ("🔍 Search", stats['search_cache'])
        ]
        
        for cache_name, cache_stats in caches:
            hit_rate = cache_stats['hit_rate']
            size = cache_stats['size']
            max_size = cache_stats['max_size']
            cache_details += f"{cache_name}: {size}/{max_size} ({hit_rate}% hit)\n"
        
        embed.add_field(
            name="💾 Cache Details",
            value=cache_details,
            inline=False
        )
        
        # Top cached items
        if efficiency['top_cached_items']:
            top_items = ""
            for i, item in enumerate(efficiency['top_cached_items'][:5], 1):
                cache_type = item['type'].replace('_', ' ').title()
                top_items += f"{i}. {cache_type} (×{item['access_count']})\n"
            
            embed.add_field(
                name="🔥 Most Accessed",
                value=top_items,
                inline=True
            )
        
        embed.set_footer(text=f"Cache Dir Size: {stats['cache_dir_size'] // 1024}KB • Use ?cache_clear to reset")
        await ctx.send(embed=embed)

    @commands.command(name='cache_clear', aliases=['clearcache', 'resetcache'])
    @commands.has_permissions(administrator=True)
    async def clear_cache(self, ctx):
        """Clear all cache data (Admin only)."""
        
        # Get stats before clearing
        before_stats = cache_manager.get_comprehensive_stats()
        before_entries = before_stats['total_entries']
        
        # Clear all caches
        cache_manager.metadata_cache.clear()
        cache_manager.stream_cache.clear()
        cache_manager.playlist_cache.clear()
        cache_manager.search_cache.clear()
        
        embed = discord.Embed(
            title="🧹 Cache Cleared",
            description="All cache data has been cleared",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="📊 Cleared Data",
            value=f"**Total Entries:** {before_entries}\n"
                  f"**Cache Types:** 4 (metadata, stream, playlist, search)\n"
                  f"**Disk Space:** Freed on next cleanup",
            inline=True
        )
        
        embed.add_field(
            name="⚠️ Impact",
            value="**Next requests will be slower**\n"
                  "**Cache will rebuild automatically**\n"
                  "**Performance will improve over time**",
            inline=True
        )
        
        embed.set_footer(text="Cache performance will rebuild as songs are played")
        await ctx.send(embed=embed)

    @commands.command(name='cache_warm', aliases=['warmcache'])
    @commands.has_permissions(administrator=True)
    async def warm_cache(self, ctx, *, songs: str = ""):
        """Pre-warm cache with popular songs (Admin only)."""
        
        if not songs:
            # Default popular songs for warming
            popular_songs = [
                "never gonna give you up",
                "bohemian rhapsody queen",
                "shape of you ed sheeran",
                "despacito luis fonsi",
                "bad habits ed sheeran",
                "blinding lights the weeknd",
                "stay the kid laroi",
                "heat waves glass animals"
            ]
        else:
            # User provided songs
            popular_songs = [song.strip() for song in songs.split(',')]
        
        embed = discord.Embed(
            title="🔥 Cache Warming",
            description=f"Pre-loading {len(popular_songs)} popular songs...",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="🎵 Songs to Cache",
            value="\n".join(f"• {song}" for song in popular_songs[:10]),
            inline=False
        )
        
        if len(popular_songs) > 10:
            embed.add_field(
                name="➕ Additional",
                value=f"... and {len(popular_songs) - 10} more songs",
                inline=False
            )
        
        embed.set_footer(text="This may take a few minutes...")
        
        msg = await ctx.send(embed=embed)
        
        # Start cache warming in background
        try:
            await cache_manager.warm_cache_for_popular_songs(popular_songs)
            
            # Update embed with results
            embed.title = "✅ Cache Warming Complete"
            embed.description = f"Successfully pre-loaded {len(popular_songs)} songs"
            embed.color = discord.Color.green()
            
            await msg.edit(embed=embed)
            
        except Exception as e:
            embed.title = "❌ Cache Warming Failed"
            embed.description = f"Error during cache warming: {str(e)}"
            embed.color = discord.Color.red()
            await msg.edit(embed=embed)

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(Info(bot))