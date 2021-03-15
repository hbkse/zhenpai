import logging

from discord import File
from discord.ext import commands
from discord.embeds import Embed
from discord import ActivityType

import asyncio

SPOTIFY_ROLE_NAME = "now_playing"
BACKGROUND_TASK_LOOP_SECONDS = 20

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
        self.guilds = [self.bot.get_guild(768301241389678603)] #testing
        print(self.guilds)
        '''
        It would probably be better to check if the role hasn't been created yet 
        by storing the role id in db, instead of checking by name
        '''
        for guild in self.guilds:
            for role in guild.roles:
                if role.name == SPOTIFY_ROLE_NAME:
                    guild_id_to_role_dict[guild.id] = role
                    break
            if guild.id not in guild_id_to_role_dict:
                guild_id_to_role_dict[guild.id] = await guild.create_role(name=SPOTIFY_ROLE_NAME, hoist=true)

        while not self.bot.is_closed():
            for guild in self.guilds:
                # get spotify role id of this guild, create if does not exist
                spotify_role = guild_id_to_role_dict[guild.id]
                for member in guild.members:
                    if member.activity == ActivityType.listening:
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