import logging

import discord
import datetime
from discord.ext import commands
from bot import Zhenpai

log: logging.Logger = logging.getLogger(__name__)

REMINDER_LOOP_MINUTES = 1

class Reposts(commands.Cog):
    """ Leaves a raised eyebrow react on messages that are recent reposts. """

    def __init__(self, bot: Zhenpai):
        self.bot = bot