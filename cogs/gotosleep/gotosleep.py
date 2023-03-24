from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
import logging
import time

log: logging.Logger = logging.getLogger(__name__)

DAY_OPTIONS = ['All', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

class GoToSleep(commands.Cog):
    """
    For people who can't control themselves and sleep on time.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        # create gotosleep role if does not exist in guild
        pass

    @app_commands.command()
    @app_commands.describe(time='The time to sleep at. ex. 23:30', day='The day to set the time for.')
    @app_commands.choices(day=[app_commands.Choice(value=day, name=day) for day in DAY_OPTIONS])
    async def sleep(self, interaction: discord.Interaction, time: str, day: Optional[str]):
        """ Set the time to sleep at. Bot will automatically assign the gotosleep role to you at the specified time. """
        pass

    @app_commands.command()
    @app_commands.describe(time='The time to wake up at. ex. 9:30', day='The day to set the time for.')
    @app_commands.choices(day=[app_commands.Choice(value=day, name=day) for day in DAY_OPTIONS])
    async def wakeup(self, interaction: discord.Interaction, time: str, day: Optional[str]):
        """ Set the time to wake up at. Bot will automatically remove the gotosleep role from you at the specified time. """
        pass

    @app_commands.command()
    async def snooze(self, interaction: discord.Interaction):
        """ Deactivate gotosleep until you turn it back on. """
        pass

    @app_commands.command()
    async def unsnooze(self, interaction: discord.Interaction):
        """ Turn gotosleep back on. """
        pass

    @app_commands.command()
    async def display(self, interaction: discord.Interaction):
        """Displays currently set times"""
        pass
    
    async def update_roles(self):
        """
        """
        pass
    

        