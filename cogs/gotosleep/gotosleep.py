import logging

from discord import File
from discord.ext import commands
from discord.embeds import Embed
from discord import ActivityType, Status

log: logging.Logger = logging.getLogger(__name__)

class GoToSleep(commands.Cog):
    """
    For people who can't control themselves and sleep on time.
    """

    def __init__(self, bot: commands.Bot):
        pass

    def bot_check_once(self):
        # check the role is created in this guild
        pass
    
    async def update_roles(self):
        """
        """
        pass
    

        