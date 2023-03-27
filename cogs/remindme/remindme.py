import logging

import discord
from discord.ext import tasks, commands
from bot import Zhenpai
from .db import ReminderDb

log: logging.Logger = logging.getLogger(__name__)

class RemindMe(commands.Cog):
    """ Remind me to do something in the future. """

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.db = ReminderDb(self.bot.pool)

    @commands.command()
    async def remindme(self, ctx: commands.Context, time: str, *, message: str):
        """Remind me to do something in the future."""
        pass