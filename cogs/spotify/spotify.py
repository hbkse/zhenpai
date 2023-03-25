import logging

import discord
from discord.ext import tasks, commands
from discord import ActivityType, Status
from bot import Zhenpai

SPOTIFY_ROLE_NAME = "Spotify"
BACKGROUND_TASK_LOOP_SECONDS = 15

log: logging.Logger = logging.getLogger(__name__)

class Spotify(commands.Cog):
    """ For highlighting and hoisting people who are listening to Spotify """

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.update_roles.start()

    async def _role_setup(self):
        """ Create the spotify role in each guild if it doesn't exist. """

        for guild in self.bot.guilds:
            if not self._get_spotify_role(guild):
                try:
                    await guild.create_role(name=SPOTIFY_ROLE_NAME, hoist=True)
                    log.info("created spotify role in {}".format(guild))
                except:
                    log.info("failed to create spotify role in {}".format(guild))

    def cog_unload(self):
        self.update_roles.cancel()

    def _get_spotify_role(self, guild: discord.Guild) -> discord.Role:
        """ Get the spotify role. """

        return discord.utils.get(guild.roles, name=SPOTIFY_ROLE_NAME) 

    @tasks.loop(seconds=BACKGROUND_TASK_LOOP_SECONDS)
    async def update_roles(self):
        """ Add or remove the spotify role from members who are listening to spotify """
            
        for guild in self.bot.guilds:
            spotify_role = self._get_spotify_role(guild)
            assert spotify_role is not None, "Spotify role not found in guild {}".format(guild)
            filtered_members = [m for m in guild.members if m.status != Status.offline and not m.bot]
            for member in filtered_members:
                activity_types = [a.type for a in member.activities]
                if ActivityType.listening in activity_types and ActivityType.playing not in activity_types:
                    await member.add_roles(spotify_role)
                else:
                    await member.remove_roles(spotify_role)

    @update_roles.before_loop
    async def before_update_roles(self):
        await self.bot.wait_until_ready()
        await self._role_setup()
        log.info("Starting spotify role update loop")