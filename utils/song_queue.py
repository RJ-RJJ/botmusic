"""
SongQueue class for Discord Music Bot
Custom queue implementation with additional features
"""
import asyncio
import itertools
import random

class SongQueue(asyncio.Queue):
    """Custom queue for songs with additional functionality"""
    
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
        """Clear all songs from the queue"""
        self._queue.clear()

    def shuffle(self):
        """Shuffle the current queue"""
        random.shuffle(self._queue)

    def remove(self, index: int):
        """Remove a song at the specified index"""
        del self._queue[index]