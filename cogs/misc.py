import discord
from discord.ext import commands
import logging

log: logging.Logger = logging.getLogger(__name__)

class Misc(commands.Cog):
    """Miscellaneous commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: commands.Context):
        await ctx.send('pong')

    @commands.command()
    async def echo(self, ctx: commands.Context, content):
        await ctx.send(content)

async def setup(bot):
    await bot.add_cog(Misc(bot))