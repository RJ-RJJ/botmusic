"""
Centralized Error Handler for Discord Music Bot
Handles all errors with user-friendly messages and proper logging
"""
import discord
from discord.ext import commands
import traceback
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from utils.exceptions import VoiceError, YTDLError

# Configure logging for error handler
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_errors.log', encoding='utf-8')
    ]
)

logger = logging.getLogger('ErrorHandler')

class ErrorCategory:
    """Error categories with different handling approaches"""
    USER_ERROR = "user_error"           # User mistakes (wrong command usage, etc.)
    VOICE_ERROR = "voice_error"         # Voice connection issues
    MUSIC_ERROR = "music_error"         # Music playback/loading issues
    PERMISSION_ERROR = "permission_error"  # Missing permissions
    SYSTEM_ERROR = "system_error"       # Internal bot errors
    NETWORK_ERROR = "network_error"     # Network/API issues
    UNKNOWN_ERROR = "unknown_error"     # Unexpected errors

class MusicBotErrorHandler:
    """Centralized error handling system"""
    
    def __init__(self):
        self.error_counts = {}
        self.error_messages = {
            # User-friendly error messages
            ErrorCategory.USER_ERROR: {
                'title': '❌ Command Error',
                'color': discord.Color.orange(),
                'help_text': 'Check your command usage with `?help`'
            },
            ErrorCategory.VOICE_ERROR: {
                'title': '🔊 Voice Error', 
                'color': discord.Color.red(),
                'help_text': 'Make sure you\'re in a voice channel and I have permissions'
            },
            ErrorCategory.MUSIC_ERROR: {
                'title': '🎵 Music Error',
                'color': discord.Color.red(),
                'help_text': 'Try a different song or check if the URL is valid'
            },
            ErrorCategory.PERMISSION_ERROR: {
                'title': '🔒 Permission Error',
                'color': discord.Color.red(),
                'help_text': 'I need proper permissions to execute this command'
            },
            ErrorCategory.SYSTEM_ERROR: {
                'title': '⚙️ System Error',
                'color': discord.Color.dark_red(),
                'help_text': 'An internal error occurred. Please try again later'
            },
            ErrorCategory.NETWORK_ERROR: {
                'title': '🌐 Network Error',
                'color': discord.Color.orange(),
                'help_text': 'Network or service issues. Please try again'
            },
            ErrorCategory.UNKNOWN_ERROR: {
                'title': '❓ Unexpected Error',
                'color': discord.Color.dark_red(),
                'help_text': 'An unexpected error occurred. Please report this'
            }
        }
    
    def categorize_error(self, error: Exception, ctx: Optional[commands.Context] = None) -> str:
        """Categorize error based on type and context"""
        
        # Command-specific errors
        if isinstance(error, commands.CommandError):
            if isinstance(error, commands.MissingRequiredArgument):
                return ErrorCategory.USER_ERROR
            elif isinstance(error, commands.BadArgument):
                return ErrorCategory.USER_ERROR
            elif isinstance(error, commands.CommandNotFound):
                return ErrorCategory.USER_ERROR
            elif isinstance(error, commands.MissingPermissions):
                return ErrorCategory.PERMISSION_ERROR
            elif isinstance(error, commands.BotMissingPermissions):
                return ErrorCategory.PERMISSION_ERROR
            elif isinstance(error, commands.NoPrivateMessage):
                return ErrorCategory.USER_ERROR
            elif isinstance(error, commands.DisabledCommand):
                return ErrorCategory.USER_ERROR
            elif isinstance(error, commands.CommandOnCooldown):
                return ErrorCategory.USER_ERROR
        
        # Music bot specific errors
        elif isinstance(error, VoiceError):
            return ErrorCategory.VOICE_ERROR
        elif isinstance(error, YTDLError):
            return ErrorCategory.MUSIC_ERROR
        
        # Network/connection errors
        elif isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorCategory.NETWORK_ERROR
        elif 'network' in str(error).lower() or 'connection' in str(error).lower():
            return ErrorCategory.NETWORK_ERROR
        elif 'timeout' in str(error).lower():
            return ErrorCategory.NETWORK_ERROR
        
        # Permission errors
        elif isinstance(error, discord.Forbidden):
            return ErrorCategory.PERMISSION_ERROR
        elif isinstance(error, discord.NotFound):
            return ErrorCategory.USER_ERROR
        
        # System errors
        elif isinstance(error, (MemoryError, OSError)):
            return ErrorCategory.SYSTEM_ERROR
        
        # Default to unknown
        else:
            return ErrorCategory.UNKNOWN_ERROR
    
    def get_user_friendly_message(self, error: Exception, category: str, ctx: Optional[commands.Context] = None) -> Dict[str, Any]:
        """Generate user-friendly error message"""
        
        base_info = self.error_messages.get(category, self.error_messages[ErrorCategory.UNKNOWN_ERROR])
        
        # Specific error messages
        specific_message = self._get_specific_message(error, category, ctx)
        
        return {
            'title': base_info['title'],
            'description': specific_message,
            'color': base_info['color'],
            'help_text': base_info['help_text']
        }
    
    def _get_specific_message(self, error: Exception, category: str, ctx: Optional[commands.Context] = None) -> str:
        """Get specific error message based on error type"""
        
        if category == ErrorCategory.USER_ERROR:
            if isinstance(error, commands.MissingRequiredArgument):
                return f"Missing required parameter: `{error.param.name}`"
            elif isinstance(error, commands.BadArgument):
                return f"Invalid argument provided: {str(error)}"
            elif isinstance(error, commands.CommandNotFound):
                return "Command not found. Use `?help` to see available commands."
            elif isinstance(error, commands.NoPrivateMessage):
                return "This command cannot be used in direct messages."
            elif isinstance(error, commands.DisabledCommand):
                return "This command is currently disabled."
            elif isinstance(error, commands.CommandOnCooldown):
                return f"Command is on cooldown. Try again in {error.retry_after:.1f} seconds."
        
        elif category == ErrorCategory.VOICE_ERROR:
            if "not connected" in str(error).lower():
                return "You need to be in a voice channel to use this command."
            elif "already in" in str(error).lower():
                return "I'm already connected to a different voice channel."
            else:
                return f"Voice connection issue: {str(error)}"
        
        elif category == ErrorCategory.MUSIC_ERROR:
            if "couldn't find" in str(error).lower():
                return "Couldn't find any music matching your search."
            elif "unavailable" in str(error).lower():
                return "This music is unavailable or has been removed."
            elif "private" in str(error).lower():
                return "This music is private and cannot be played."
            else:
                return f"Music playback error: {str(error)}"
        
        elif category == ErrorCategory.PERMISSION_ERROR:
            if isinstance(error, commands.MissingPermissions):
                perms = ', '.join(error.missing_permissions)
                return f"You need these permissions: {perms}"
            elif isinstance(error, commands.BotMissingPermissions):
                perms = ', '.join(error.missing_permissions)
                return f"I need these permissions: {perms}"
            else:
                return "Permission denied for this operation."
        
        elif category == ErrorCategory.NETWORK_ERROR:
            return "Network connection issue. Please try again in a moment."
        
        elif category == ErrorCategory.SYSTEM_ERROR:
            return "Internal system error. The issue has been logged."
        
        else:
            return f"An unexpected error occurred: {str(error)[:100]}"
    
    async def handle_error(self, error: Exception, ctx: Optional[commands.Context] = None, 
                          additional_info: Optional[str] = None) -> bool:
        """Main error handling method"""
        
        try:
            # Categorize the error
            category = self.categorize_error(error, ctx)
            
            # Update error statistics
            self._update_error_stats(category, error)
            
            # Log the error
            self._log_error(error, category, ctx, additional_info)
            
            # Send user-friendly message
            if ctx and ctx.channel:
                await self._send_error_message(error, category, ctx)
            
            # Handle automatic recovery if possible
            await self._attempt_recovery(error, category, ctx)
            
            return True
            
        except Exception as e:
            # Fallback error handling
            logger.critical(f"Error in error handler: {e}")
            if ctx:
                try:
                    await ctx.send("❌ A critical error occurred. Please try again later.")
                except:
                    pass
            return False
    
    def _update_error_stats(self, category: str, error: Exception):
        """Update error statistics for monitoring"""
        if category not in self.error_counts:
            self.error_counts[category] = {}
        
        error_type = type(error).__name__
        if error_type not in self.error_counts[category]:
            self.error_counts[category][error_type] = 0
        
        self.error_counts[category][error_type] += 1
    
    def _log_error(self, error: Exception, category: str, ctx: Optional[commands.Context], 
                   additional_info: Optional[str]):
        """Log error with appropriate level"""
        
        error_info = {
            'category': category,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'guild': ctx.guild.name if ctx and ctx.guild else 'DM',
            'user': str(ctx.author) if ctx else 'System',
            'command': ctx.command.name if ctx and ctx.command else 'Unknown',
            'additional_info': additional_info
        }
        
        # Choose log level based on category
        if category in [ErrorCategory.SYSTEM_ERROR, ErrorCategory.UNKNOWN_ERROR]:
            logger.error(f"Error: {error_info}", exc_info=True)
        elif category == ErrorCategory.NETWORK_ERROR:
            logger.warning(f"Network Error: {error_info}")
        else:
            logger.info(f"User Error: {error_info}")
    
    async def _send_error_message(self, error: Exception, category: str, ctx: commands.Context):
        """Send user-friendly error message"""
        
        message_info = self.get_user_friendly_message(error, category, ctx)
        
        embed = discord.Embed(
            title=message_info['title'],
            description=message_info['description'],
            color=message_info['color'],
            timestamp=datetime.utcnow()
        )
        
        # Add help text
        embed.add_field(
            name="💡 Help",
            value=message_info['help_text'],
            inline=False
        )
        
        # Add command info if available
        if ctx.command:
            embed.add_field(
                name="📝 Command",
                value=f"`?{ctx.command.qualified_name}`",
                inline=True
            )
        
        # Add guild info for debugging
        if category in [ErrorCategory.SYSTEM_ERROR, ErrorCategory.UNKNOWN_ERROR]:
            embed.set_footer(text=f"Error ID: {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
        
        try:
            await ctx.send(embed=embed)
        except discord.Forbidden:
            # Fallback to simple message if embed permissions missing
            await ctx.send(f"{message_info['title']}: {message_info['description']}")
        except Exception:
            # Last resort fallback
            await ctx.send("❌ An error occurred and I couldn't send the error message.")
    
    async def _attempt_recovery(self, error: Exception, category: str, ctx: Optional[commands.Context]):
        """Attempt automatic recovery for certain error types"""
        
        if category == ErrorCategory.VOICE_ERROR and ctx:
            # Try to reconnect to voice if possible
            try:
                if hasattr(ctx, 'voice_state') and ctx.voice_state:
                    await ctx.voice_state._restart_audio_player_if_needed()
            except Exception as e:
                logger.info(f"Auto-recovery failed: {e}")
        
        elif category == ErrorCategory.MUSIC_ERROR and ctx:
            # Try to skip problematic song and continue
            try:
                if hasattr(ctx, 'voice_state') and ctx.voice_state and ctx.voice_state.is_playing:
                    ctx.voice_state.skip()
                    await ctx.send("⏭️ Skipped problematic song and continuing...")
            except Exception as e:
                logger.info(f"Auto-skip failed: {e}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        total_errors = sum(
            sum(error_counts.values()) for error_counts in self.error_counts.values()
        )
        
        return {
            'total_errors': total_errors,
            'by_category': dict(self.error_counts),
            'most_common': self._get_most_common_errors()
        }
    
    def _get_most_common_errors(self) -> list:
        """Get most common errors across all categories"""
        all_errors = []
        for category, errors in self.error_counts.items():
            for error_type, count in errors.items():
                all_errors.append({
                    'category': category,
                    'type': error_type,
                    'count': count
                })
        
        return sorted(all_errors, key=lambda x: x['count'], reverse=True)[:5]

# Global error handler instance
error_handler = MusicBotErrorHandler()