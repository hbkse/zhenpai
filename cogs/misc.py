import discord
from discord.ext import commands
import config
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

    @commands.command()
    @commands.is_owner()
    async def debug(self, ctx: commands.Context):
        message = [
            f'Logged in as: {self.bot.user}',
            f'Discord.py version: {discord.__version__}',
            f'Visible guilds: {self.bot.guilds}',
            f'Commit hash: {config.COMMIT_HASH}'
        ]
        log.info("Debug command used.")

        await ctx.send("\n".join(message))

async def setup(bot):
    await bot.add_cog(Misc(bot))