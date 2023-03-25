from typing import Optional
from bot import Zhenpai

import discord
from discord import app_commands
from discord.ext import tasks, commands
import logging
import datetime
import re
from .db import GoToSleepDb

log: logging.Logger = logging.getLogger(__name__)

DAY_OPTIONS = ['All', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
GOTOSLEEP_ROLE_NAME = 'zhenpai-gotosleep'
POLLING_INTERVAL = 1

class GoToSleep(commands.Cog):
    """ For people who can't control themselves and sleep on time. """

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.db = GoToSleepDb(self.bot.db_pool)
        self.update_roles.start()  

    def cog_unload(self):
        self.update_roles.cancel()

    def _get_gotosleep_role(self, guild: discord.Guild) -> discord.Role:
        """ Get the gotosleep role. """

        return discord.utils.get(guild.roles, name=GOTOSLEEP_ROLE_NAME) 
    
    def _convert_time(self, time: str) -> datetime.time:
        """ Convert the time from a string to an datetime. """

        # regex for "23:30"
        time_regex = re.compile(r'^([01]\d|2[0-3]):([0-5]\d)$')
        hour, minute = map(int, time_regex.match(time).groups())
        return datetime.time(hour, minute)
    
    def _is_time_inbetween(self, time: datetime.time, start: datetime.time, end: datetime.time) -> bool:
        """ Check if a time is inbetween two other times, including wrapping around. """

        if start <= end:
            return start <= time <= end
        else:
            return start <= time or time <= end
    
    async def _setup_new_user_if_needed(self, interaction: discord.Interaction):
        """ Add a new user to the database with default values. """

        user_exists = await self.db.check_user_exists(interaction.user.id, interaction.guild.id)
        if not user_exists:
            log.info(f'Adding new user {interaction.user.id} to database {interaction.guild.id}')
            await self.db.add_user(interaction.user.id, interaction.guild.id)

    @app_commands.command()
    @app_commands.describe(
        sleep_time='The time to sleep at. ex. 23:30', 
        wake_time='The time to wake up at. ex. 7:30',
        day='The day to set the time for.')
    @app_commands.choices(day=[app_commands.Choice(value=day, name=day) for day in DAY_OPTIONS])
    async def sleep(self, interaction: discord.Interaction, sleep_time: str, wake_time: str, day: Optional[str]):
        """ Set the time to sleep at. Bot will automatically assign the gotosleep role to you at the specified time. """

        await self._setup_new_user_if_needed(interaction)
        converted_start_time = self._convert_time(sleep_time)
        converted_end_time = self._convert_time(wake_time)
        if day is None or day == 'All':
            await self.db.update_all_times(interaction.user.id, interaction.guild_id, converted_start_time, converted_end_time)
        else:
            await self.db.update_single_time(interaction.user.id, interaction.guild_id, day.lower(), converted_start_time, converted_end_time)
        await interaction.response.send_message(f'Successfully set times.', ephemeral=True)

    @app_commands.command()
    async def snooze(self, interaction: discord.Interaction, on_or_off: bool = False):
        """ Deactivate gotosleep until you turn it back on. """

        await self._setup_new_user_if_needed(interaction)
        await self.db.set_user_active(interaction.user.id, interaction.guild.id, on_or_off)
        await interaction.response.send_message('gotosleep is now off.', ephemeral=True)

    @app_commands.command()
    async def display(self, interaction: discord.Interaction):
        """Displays currently set times"""

        await self._setup_new_user_if_needed(interaction)
        record = await self.db.get_by_user_id(interaction.user.id, interaction.guild.id)
        embed = discord.Embed(title='gotosleep', description='The times you have set for sleeping and waking up.')
        active_text = bool(record['active']) and 'gotosleep is currently on.' or 'gotosleep is currently off.'
        embed.set_footer(text=active_text)
        for day in DAY_OPTIONS[1:]:
            embed.add_field(name=day, value=f'{record[day.lower() + "_start_time"]} - {record[day.lower() + "_end_time"]}')
        await interaction.response.send_message(embed=embed)

    @tasks.loop(minutes=POLLING_INTERVAL)
    async def update_roles(self):
        """
        Check if it's time to add or remove the gotosleep role.
        """

        the_entire_table = await self.db.get_all_users_global()
        log.info(f'Scanned the entire gotosleep table. Found {len(the_entire_table)} records.')
        todays_day = datetime.datetime.today().strftime('%A').lower()
        for record in the_entire_table:
            start = record[todays_day + '_start_time']
            end = record[todays_day + '_end_time']
            guild_id = record['guild_id']
            user_id = record['user_id']
            active = record['active']

            guild = self.bot.get_guild(guild_id)
            member = guild.get_member(user_id)
            role = self._get_gotosleep_role(guild)

            # if any of these are true, let's just remove the role to be safe
            if not active or start is None or end is None:
                log.info(f'Removing role from {member} in {guild}.')
                await member.remove_roles(role)
                continue

            if self._is_time_inbetween(datetime.datetime.now().time(), start, end):
                log.info(f'Adding role to {member} in {guild}.')
                await member.add_roles(role)
            else:
                log.info(f'Removing role from {member} in {guild}.')
                await member.remove_roles(role)

    async def _set_up_role_and_channel_permissions(self, guild: discord.Guild) -> None:
        """ Create the gotosleep role and set permission override for all existing channels. """

        # create role if it doesn't exist
        if not (gotosleep_role := self._get_gotosleep_role(guild)):
            try:
                await guild.create_role(name=GOTOSLEEP_ROLE_NAME)
                log.info(f'Created gotosleep role in {guild}')
            except:
                log.info(f'Failed to create gotosleep role in {guild}')
                return
            
        # set permissions every time, in case new channels have been created
        for channel in guild.channels:
            print(channel)
            await channel.set_permissions(gotosleep_role, view_channel=False)

    @update_roles.before_loop
    async def before_update_roles(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self._set_up_role_and_channel_permissions(guild)
        log.info("Starting gotosleep role update loop")

    # TODO: need to set up event to update permissions when new channel is created?
    # TODO: need to add an option to dm the bot and force remove your role
    # TODO: removing the role from everyone when the bot is down
    # TODO: need to skip admins? cant believe the task crashes with 403