"""
Info Cog for Discord Music Bot
Contains help, stats, and platform information commands
"""
import discord
from discord.ext import commands
import platform
from config.settings import PREFIX
from utils.helpers import get_server_count, get_simple_status_messages

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

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(Info(bot))