import logging

from discord import File
from discord.ext import commands
from discord.embeds import Embed
from discord import ActivityType

import asyncio

SPOTIFY_ROLE_NAME = "now_playing"
BACKGROUND_TASK_LOOP_SECONDS = 15

class Spotify(commands.Cog):
    """
    """

    def __init__(self, bot):
        self.bot = bot
        self.guilds = None
        self.guild_id_to_role_dict = {}
        self.bg_task = self.bot.loop.create_task(self.update_roles())

    async def update_roles(self):
        """
        """
        await self.bot.wait_until_ready()
        self.guilds = self.bot.guilds
        '''
        It would probably be better to check if the role hasn't been created yet 
        by storing the role id in db, instead of checking by name, especially because 
        role names can be the same
        '''
        for guild in self.guilds:
            for role in guild.roles:
                if role.name == SPOTIFY_ROLE_NAME:
                    self.guild_id_to_role_dict[guild.id] = role
                    break
            if guild.id not in self.guild_id_to_role_dict:
                self.guild_id_to_role_dict[guild.id] = await guild.create_role(name=SPOTIFY_ROLE_NAME, hoist=True)

        while not self.bot.is_closed():
            for guild in self.guilds:
                spotify_role = self.guild_id_to_role_dict[guild.id]
                for member in guild.members:
                    if any(activity.type == ActivityType.listening for activity in member.activities):
                        try:
                            await member.add_roles(spotify_role)
                        except:
                            await self.bot.get_user(self.bot.owner_id).send("bot failed to add role. guild: {} member: {}".format(guild, member))
                    else:
                        try:
                            await member.remove_roles(spotify_role)
                        except:
                            await self.bot.get_user(self.bot.owner_id).send("bot failed to remove role. guild: {} member: {}".format(guild, member))
            await asyncio.sleep(BACKGROUND_TASK_LOOP_SECONDS)