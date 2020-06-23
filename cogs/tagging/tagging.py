import atexit
import logging
from pathlib import Path
from discord import File
from discord.ext import commands
from discord.embeds import Embed

from .kvstore import *
from . import constants
from . import taggingutils

"""
WIP: 
Figure out command groups
Figure out user information
Figure out global vs server tags
"""


class Tagging(commands.Cog):
    """Keyword tagging, WIP"""

    def __init__(self, bot):
        Path(constants.IMAGES_PATH).mkdir(parents=True, exist_ok=True)
        Path(constants.DB_PATH).mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger('zhenpai.tagging')
        self.bot = bot
        self.lookup = DictKeyValueStore()
        # self.lookup = RedisKeyValueStore(ip='localhost', port=6379)
        self.usage = None  # TODO
        atexit.register(self.cleanup)

    @commands.group()
    async def tag(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Valid subcommands are \'create\', \'list\', and \'delete\'.')

    @tag.command()
    async def create(self, ctx: commands.Context, tag_name: str, link: str = None):
        """
        Creates and links a tag to an image.
        Valid command formats:
            "z!create foo" with an attachment of an image named bar
            "z!create foo https://path.to/bar.png"
        """
        attachments = ctx.message.attachments
        if tag_name and attachments:
            attachment = attachments[0]
            command_name = taggingutils.sanitize(tag_name)
            guild_id = ctx.guild.id
            key = taggingutils.create_redis_key(guild_id, command_name)
            server_path = path.join(constants.IMAGES_PATH, str(guild_id))
            Path(server_path).mkdir(parents=True, exist_ok=True)
            local_url = path.join(server_path, attachment.filename)
            await attachment.save(local_url)
            self.logger.info("Saved image to %s", local_url)
            self.lookup[key] = TaggingItem(name=command_name,
                                           url=attachment.url,
                                           local_url=local_url,
                                           creator_id=ctx.message.author.id)
            await ctx.send(
                content='Successfully created ' + command_name + ' linked to ' + self.lookup[key].local_url)
            self.logger.info('Successfully created %s linked to %s', command_name, self.lookup[key].local_url)
        elif tag_name and link:
                pass
                # TODO: sanitize and check that the second argument is an URL.
        else:
            await ctx.send('Usage: z!create <tag name: str> with an attachment')

    @tag.command()
    async def list(self, ctx):
        """Lists out all tags."""
        embed = Embed(title='List of Registered Tags')
        if isinstance(self.lookup, DictKeyValueStore):
            for k, v in self.lookup.get_paged(server_id=str(ctx.guild.id)).items():
                creator = await self.bot.fetch_user(v.creator_id)
                embed = embed.add_field(name=v.name,
                                        value="[Link]({link})\nCreator: {creator}"
                                        .format(link=v.url, creator=creator.name))
        elif isinstance(self.lookup, RedisKeyValueStore):
            cursor, keys = self.lookup.get_paged(server_id=ctx.guild.id)
            for k in keys:
                v = self.lookup[k]
                creator = await self.bot.fetch_user(v.creator_id)
                embed = embed.add_field(name=v.name,
                                        value="[Link]({link})\nCreator: {creator}"
                                        .format(link=v.url, creator=creator.name))
        await ctx.send(embed=embed)

    @tag.command()
    async def delete(self, ctx: commands.Context, *args):
        for tag_name in args:
            key_name = taggingutils.create_redis_key(ctx.guild.id, tag_name)
            self.lookup.delete(key_name)
    
    @tag.command()
    async def debug(self, ctx):
        """Used for debugging"""
        pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.author.bot:
            words = taggingutils.parse_message(message)
            for word in words:
                word = taggingutils.sanitize(word)
                key = taggingutils.create_redis_key(message.guild.id, word)
                if key in self.lookup:
                    await message.channel.send(file=File(self.lookup[key].local_url))
                    self.mark_usage(key)
                    break  # only allow one match per message

    def mark_usage(self, tag):
        pass

    def cleanup(self):
        self.lookup.save()
