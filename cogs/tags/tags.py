import discord
from discord.ext import commands
import logging

log: logging.Logger = logging.getLogger(__name__)

class Tags(commands.Cog):
    """For saving and retrieving things"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def save(self, ctx: commands.Context):
        # get existing tags in this guild
        # check set of valid message commands for the bot, make sure no overlap
        # save the tag
        pass