import discord
from discord.ext import commands
import logging
from .db import TagsDb
from bot import Zhenpai

log: logging.Logger = logging.getLogger(__name__)

class Tags(commands.Cog):
    """ For saving and retrieving things """

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.db = TagsDb(self.bot.db_pool)

    @commands.command()
    async def save(self, ctx: commands.Context, tag_name: str, *, content: str) -> None:
        """ Save a tag """

        existing_tags = await self.db.get_all_tags_in_guild(ctx.guild.id)
        existing_tag_names = [tag['tag'] for tag in existing_tags]
        if tag_name in existing_tag_names:
            await ctx.send(f'Tag **{tag_name}** already exists')
            return
        if tag_name in self.bot.all_commands:
            await ctx.send(f'Tag **{tag_name}** conflicts with an existing command')
            return

        await self.db.create_tag(tag_name, content, ctx.guild.id, ctx.author.id)
        await ctx.send(f'Tag **{tag_name}** created.')

    @commands.command()
    async def update(self, ctx: commands.Context, tag_name: str, *, content: str) -> None:
        """ Update an existing tag """

        existing_tags = await self.db.get_all_tags_in_guild(ctx.guild.id)
        existing_tag_names = [tag['tag'] for tag in existing_tags]
        if tag_name not in existing_tag_names:
            await ctx.send(f"Tag **{tag_name}** doesn't exist")
            return

        await self.db.update_tag(tag_name, content, ctx.guild.id, ctx.author.id)
        await ctx.send(f'Tag **{tag_name}** updated.')

    @commands.command()
    async def delete(self, ctx: commands.Context, tag_name: str) -> None:
        """ Delete a tag """

        res = await self.db.delete_tag(tag_name, ctx.guild.id)
        if res:
            await ctx.send(f'Tag **{tag_name}** deleted.')
        else:   
            await ctx.send(f"Tag **{tag_name}** doesn't exist")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """ Check messages for tags """

        if message.author.bot:
            return

        prefix = self.bot.command_prefix
        if message.content.startswith(prefix):
            first_token = message.content.split(' ')[0][len(prefix):]
            record = await self.db.get_tag_by_guild(first_token, message.guild.id)
            if record:
                await message.channel.send(record['content'])
        