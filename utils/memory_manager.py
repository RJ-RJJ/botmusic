"""
Memory Manager for Discord Music Bot
Handles proper cleanup and memory management for audio resources
"""
import asyncio
import gc
import psutil
import os
from typing import Optional, Dict, Any
import weakref
from datetime import datetime

class MemoryManager:
    """Centralized memory management for bot resources"""
    
    def __init__(self):
        self.tracked_objects = weakref.WeakSet()
        self.audio_sources = weakref.WeakSet() 
        self.voice_connections = weakref.WeakSet()
        self.ytdl_instances = weakref.WeakSet()
        self._cleanup_task = None
        self._stats = {
            'last_cleanup': None,
            'objects_cleaned': 0,
            'memory_freed_mb': 0.0
        }
    
    def track_object(self, obj, category: str = 'general'):
        """Track an object for memory management"""
        try:
            self.tracked_objects.add(obj)
            
            # Category-specific tracking
            if category == 'audio_source':
                self.audio_sources.add(obj)
            elif category == 'voice_connection':
                self.voice_connections.add(obj)
            elif category == 'ytdl_instance':
                self.ytdl_instances.add(obj)
                
        except TypeError:
            # Object not weakly referenceable
            pass
    
    def untrack_object(self, obj):
        """Remove object from tracking (usually automatic via WeakSet)"""
        try:
            self.tracked_objects.discard(obj)
            self.audio_sources.discard(obj)
            self.voice_connections.discard(obj)
            self.ytdl_instances.discard(obj)
        except TypeError:
            pass
    
    async def cleanup_audio_source(self, source):
        """Properly cleanup an audio source"""
        try:
            # Close FFmpeg process if exists
            if hasattr(source, 'source') and source.source:
                if hasattr(source.source, 'cleanup'):
                    source.source.cleanup()
                
                # Force close if process is still running
                if hasattr(source.source, '_process') and source.source._process:
                    try:
                        source.source._process.terminate()
                        await asyncio.sleep(0.1)
                        if source.source._process.poll() is None:
                            source.source._process.kill()
                    except:
                        pass
            
            # Clear references
            if hasattr(source, 'data'):
                source.data.clear() if isinstance(source.data, dict) else None
            
            # Remove from tracking
            self.untrack_object(source)
            
            return True
        except Exception as e:
            print(f"⚠️ Error cleaning up audio source: {e}")
            return False
    
    async def cleanup_voice_connection(self, voice):
        """Properly cleanup a voice connection"""
        try:
            if voice and voice.is_connected():
                await voice.disconnect(force=True)
            
            # Remove from tracking
            self.untrack_object(voice)
            return True
        except Exception as e:
            print(f"⚠️ Error cleaning up voice connection: {e}")
            return False
    
    async def force_garbage_collection(self):
        """Force garbage collection and return freed memory"""
        before_memory = self.get_memory_usage()
        
        # Run garbage collection multiple times for thorough cleanup
        for _ in range(3):
            gc.collect()
            await asyncio.sleep(0.01)
        
        after_memory = self.get_memory_usage()
        freed_mb = before_memory - after_memory
        
        self._stats['memory_freed_mb'] += freed_mb
        self._stats['last_cleanup'] = datetime.now()
        
        return freed_mb
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except:
            return 0.0
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percent': process.memory_percent(),
                'tracked_objects': len(self.tracked_objects),
                'audio_sources': len(self.audio_sources),
                'voice_connections': len(self.voice_connections),
                'ytdl_instances': len(self.ytdl_instances),
                'last_cleanup': self._stats['last_cleanup'],
                'total_freed_mb': self._stats['memory_freed_mb']
            }
        except:
            return {'error': 'Could not get memory stats'}
    
    async def periodic_cleanup(self, interval: int = 300):
        """Run periodic cleanup every interval seconds"""
        while True:
            try:
                await asyncio.sleep(interval)
                
                print("🧹 Starting periodic memory cleanup...")
                
                # Count objects before cleanup
                before_count = len(self.tracked_objects)
                before_memory = self.get_memory_usage()
                
                # Cleanup orphaned audio sources
                orphaned_sources = []
                for source in list(self.audio_sources):
                    try:
                        # Check if source is still being used
                        if hasattr(source, '_ctx') and source._ctx:
                            guild_id = source._ctx.guild.id
                            # Additional checks can be added here
                        else:
                            orphaned_sources.append(source)
                    except:
                        orphaned_sources.append(source)
                
                # Cleanup orphaned sources
                for source in orphaned_sources:
                    await self.cleanup_audio_source(source)
                
                # Force garbage collection
                freed_mb = await self.force_garbage_collection()
                
                after_count = len(self.tracked_objects)
                after_memory = self.get_memory_usage()
                
                cleaned_objects = before_count - after_count
                self._stats['objects_cleaned'] += cleaned_objects
                
                if cleaned_objects > 0 or freed_mb > 1.0:
                    print(f"🧹 Cleanup complete: {cleaned_objects} objects cleaned, {freed_mb:.1f}MB freed")
                    print(f"📊 Memory: {before_memory:.1f}MB → {after_memory:.1f}MB")
                
            except Exception as e:
                print(f"❌ Error in periodic cleanup: {e}")
    
    def start_periodic_cleanup(self, loop, interval: int = 300):
        """Start the periodic cleanup task"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = loop.create_task(self.periodic_cleanup(interval))
        return self._cleanup_task
    
    def stop_periodic_cleanup(self):
        """Stop the periodic cleanup task"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

# Global memory manager instance
memory_manager = MemoryManager()