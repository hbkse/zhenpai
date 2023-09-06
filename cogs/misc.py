from typing import Optional
import discord
import datetime
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
        if ctx.message.reference and (reply_msg := ctx.message.reference.resolved):
            prev_message = reply_msg
        else:
            prev_message = [message async for message in ctx.channel.history(limit=2)][1]
        content = ' '.join(prev_message.content.split(" ")[remove:])
        out = f"why are you, as a man, {content}"
        await ctx.send(out)

    @commands.command()
    async def timeout(self, ctx: commands.Context, minutes: int = 1):
        """ Time yourself out. For your own good. """
        if minutes > 1440:
            await ctx.send("You can't time yourself out for more than 1440 minutes (24 hours). Just to be safe.")
            return
        await ctx.author.timeout(datetime.timedelta(minutes=minutes))
        await ctx.send(f"Bye bye :wave:")

async def setup(bot: Zhenpai):
    await bot.add_cog(Misc(bot))