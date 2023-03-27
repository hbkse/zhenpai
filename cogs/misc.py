import discord
from discord.ext import commands
from bot import Zhenpai
import logging
import datetime

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
    async def servertime(self, ctx: commands.Context):
        await ctx.send(f'The current time is {datetime.datetime.now()}')

async def setup(bot: Zhenpai):
    await bot.add_cog(Misc(bot))