"""
Song class for Discord Music Bot
Handles song representation and embed creation
"""
import discord

class Song:
    """Represents a song with its source and requester information"""
    __slots__ = ('source', 'requester')

    def __init__(self, source):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        """Create a Discord embed for the song"""
        embed = (discord.Embed(title='Now playing',
                               description='```css\n{0.source.title}\n```'.format(self),
                               color=discord.Color.blurple())
                 .add_field(name='Duration', value=self.source.duration)
                 .add_field(name='Requested by', value=self.requester.mention)
                 .add_field(name='Uploader', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
                 .add_field(name='URL', value='[Click]({0.source.url})'.format(self))
                 .set_thumbnail(url=self.source.thumbnail))

        return embed