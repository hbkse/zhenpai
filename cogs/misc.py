from typing import Optional
import discord
from discord.ext import commands
from bot import Zhenpai
import logging

log: logging.Logger = logging.getLogger(__name__)

class Misc(commands.Cog):
    """Miscellaneous commands."""

    def __init__(self, bot: Zhenpai):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: commands.Context):
        await ctx.send('pong')

    @commands.command()
    async def echo(self, ctx: commands.Context, content):
        await ctx.send(content)

    @commands.command()
    async def asaman(self, ctx: commands.Context, remove: Optional[int] = 0):
        # get message content from reply
        if ctx.message.reference and (reply_msg := ctx.message.reference.resolved):
            prev_message = reply_msg
        else:
            prev_message = [message async for message in ctx.channel.history(limit=2)][1]
        content = ' '.join(prev_message.content.split(" ")[remove:])
        out = f"why are you, as a man, {content}"
        await ctx.send(out)

async def setup(bot: Zhenpai):
    await bot.add_cog(Misc(bot))