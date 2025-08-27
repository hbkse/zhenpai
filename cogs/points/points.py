import discord
from discord.ext import commands
import logging
from typing import Optional
from .db import PointsDb
from bot import Zhenpai

log: logging.Logger = logging.getLogger(__name__)

class Points(commands.Cog):
    """Commands for managing and betting points"""

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.db = PointsDb(self.bot.db_pool)

    # TODO: add background loop for reading for events and updating points transaction table
