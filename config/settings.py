"""
Configuration settings for Discord Music Bot
Contains all constants, environment variables, and configuration options
"""
import os
import shutil
from dotenv import load_dotenv

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

# FFmpeg executable path (local first, then system for hosting platforms)
def get_ffmpeg_executable():
    """Try to use local FFmpeg first, then system FFmpeg"""
    # Check local ffmpeg folder first
    local_ffmpeg = os.path.join(os.path.dirname(__file__), '..', 'ffmpeg', 'ffmpeg.exe')
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg
    
    # Fall back to system FFmpeg (for hosting platforms)
    return shutil.which('ffmpeg') or 'ffmpeg'

FFMPEG_EXECUTABLE = get_ffmpeg_executable()

# FFmpeg options (Enhanced for hosting stability)
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -reconnect_at_eof 1 -reconnect_on_network_error 1 -reconnect_on_http_error 4xx,5xx -http_persistent 0',
    'options': '-vn -bufsize 512k -maxrate 128k'
}

# yt-dlp options (Optimized for speed & hosting stability)
YDL_OPTIONS = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
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
    # Network & hosting optimizations
    'socket_timeout': 15,        # Longer timeout for hosting
    'retries': 3,               # More retries for network issues
    'fragment_retries': 3,      # More fragment retries
    'skip_unavailable_fragments': True,  # Skip problematic fragments
    'http_chunk_size': 10485760,  # 10MB chunks for better streaming
    'keepalive': True,          # Keep connections alive
    'prefer_free_formats': True, # Prefer formats that work better on hosting
    'force_ipv4': True,
    'geo_bypass': True,
}

# Voice State Configuration
PLAYLIST_BATCH_SIZE = 15        # Songs to load per batch
PLAYLIST_LOW_THRESHOLD = 3      # When to load next batch
CONCURRENT_LOAD_LIMIT = 4       # Max songs to load simultaneously
AUTO_DISCONNECT_DELAY = 300     # 5 minutes in seconds

# Bot Status Configuration
def get_server_count():
    """Get current server count - will be injected from main bot instance"""
    # This will be overridden in the main bot file
    return 0

def get_simple_status_messages():
    """Get simple 3-status rotation"""
    server_count = get_server_count()
    
    return [
        "?help",  # Listening to ?help
        f"{server_count} servers",  # Watching X servers
        "This bot is under development"  # Playing: This bot is under development
    ]

# Discord Intents
import discord

def get_bot_intents():
    """Get required Discord intents"""
    intents = discord.Intents.default()
    intents.message_content = True
    return intents