import logging

from discord import File
from discord.ext import commands
from discord.embeds import Embed
from discord import ActivityType, Status

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
                try: 
                    self.guild_id_to_role_dict[guild.id] = await guild.create_role(name=SPOTIFY_ROLE_NAME, hoist=True)
                except:
                    await self.send_debug_to_owner("failed to create role in {}".format(guild))

        # how very ugly... :)
        while not self.bot.is_closed():
            for guild in self.guilds:
                if guild.id not in self.guild_id_to_role_dict:
                    continue
                spotify_role = self.guild_id_to_role_dict[guild.id]
                filtered_members = [m for m in guild.members if m.status != Status.offline and not m.bot]
                for member in filtered_members:
                    types = [a.type for a in member.activities]
                    if ActivityType.listening in types and ActivityType.playing not in types:
                        try:
                            if spotify_role not in member.roles:
                                await member.add_roles(spotify_role)
                        except Exception as ex:
                            self.send_debug_to_owner("*** FAILED to ADD role to member {} \n {} \n {}".format(member, member.activities, ex))
                    else:
                        try:
                            if spotify_role in member.roles:
                                await member.remove_roles(spotify_role)
                        except Exception as ex:
                            self.send_debug_to_owner("*** FAILED to REMOVE role to member {} \n {} \n {}".format(member, member.activities, ex))
            await asyncio.sleep(BACKGROUND_TASK_LOOP_SECONDS)

    async def send_debug_to_owner(self, message: str):
        owner = self.bot.get_user(self.bot.owner_id)
        await owner.send(message)