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
# THIS IS GUNNA BREAK BECAUSE OF DAYLIGHT SAVINGS TIME RIGHT? LOL, oh well one day I'll fix it
CENTRAL_TIMEZONE_TIMEDELTA = datetime.timedelta(hours=-5) # UTC-5

class GoToSleep(commands.Cog):
    """ For people who can't control themselves and sleep on time. """

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.db = GoToSleepDb(self.bot.db_pool)
        self.update_roles.start() 
        # lmao
        self.update_roles.add_exception_type(AttributeError)

    def cog_unload(self):
        self.update_roles.cancel()

    def _get_gotosleep_role(self, guild: discord.Guild) -> discord.Role:
        """ Get the gotosleep role. """

        return discord.utils.get(guild.roles, name=GOTOSLEEP_ROLE_NAME) 
    
    def _read_time_str(self, time_str: str, utcoff: datetime.timedelta) -> datetime.time:
        """ Convert the time from a string to utc naive datetime. """

        time_regex = re.compile(r'^([0-9]|[01]\d|2[0-3]):([0-5]\d)$') # regex for "0:00 to 23:59"
        hour, minute = map(int, time_regex.match(time_str).groups())
        return self._apply_time_offset(datetime.time(hour, minute), utcoff)
    
    def _apply_time_offset(self, time: datetime.time, utcoff: datetime.timedelta) -> datetime.time:
        """ Apply utc offset to a time. """

        # convert to datetime, add utc offset, then convert back to time
        return (datetime.datetime.combine(datetime.date.today(), time) + utcoff).time()
    
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
        try:
            # convert to utc+0
            converted_start_time = self._read_time_str(sleep_time, -CENTRAL_TIMEZONE_TIMEDELTA)
            converted_end_time = self._read_time_str(wake_time, -CENTRAL_TIMEZONE_TIMEDELTA)
        except Exception as e:
            log.error(f'{e}')
            log.error(f'Unable to read the times provided. {sleep_time} {wake_time}')
            await interaction.response.send_message('Unable to read the times provided. Please use 24 hour time. ex. 00:00 to 23:59', ephemeral=True)
            return
        
        if day is None or day == 'All':
            await self.db.update_all_times(interaction.user.id, interaction.guild_id, converted_start_time, converted_end_time)
        else:
            await self.db.update_single_time(interaction.user.id, interaction.guild_id, day.lower(), converted_start_time, converted_end_time)
        await interaction.response.send_message(f'Successfully set times.', ephemeral=True)

    @app_commands.command()
    async def snooze(self, interaction: discord.Interaction):
        """ Activate/deactivate gotosleep. """

        await self._setup_new_user_if_needed(interaction)
        record = await self.db.get_by_user_id(interaction.user.id, interaction.guild.id)
        if record:
            currently_active = record['active']

        await self.db.set_user_active(interaction.user.id, interaction.guild.id, not currently_active)
        if currently_active:
            await interaction.response.send_message('gotosleep is now off.', ephemeral=True)
        else:
            await interaction.response.send_message('gotosleep is now on.', ephemeral=True)

    @app_commands.command()
    async def display(self, interaction: discord.Interaction):
        """Displays currently set times"""

        await self._setup_new_user_if_needed(interaction)
        record = await self.db.get_by_user_id(interaction.user.id, interaction.guild.id)
        if not record:
            # don't think this should ever happen, since we set up a new user if needed
            await interaction.response.send_message('You have not set any times yet. Use /sleep to set times.', ephemeral=True)
            return
        
        title = f"{interaction.user.display_name}\'s gotosleep times"
        embed = discord.Embed(title=title, description='The times you have set for sleeping and waking up. Times are in UTC (for now).', color=discord.Color.dark_teal())
        active_text = bool(record['active']) and 'gotosleep is currently on.' or 'gotosleep is currently off.'
        active_text += ' Use /snooze to turn it on or off.'
        embed.set_footer(text=active_text)
        for day in DAY_OPTIONS[1:]:
            start_time = record[day.lower() + "_start_time"]
            end_time = record[day.lower() + "_end_time"]
            # convert from utc+0 to central time
            converted_start_time = self._apply_time_offset(start_time, CENTRAL_TIMEZONE_TIMEDELTA)
            converted_end_time = self._apply_time_offset(end_time, CENTRAL_TIMEZONE_TIMEDELTA)
            embed.add_field(name=day, value=f'{converted_start_time} - {converted_end_time}')
        await interaction.response.send_message(embed=embed)

    @tasks.loop(minutes=POLLING_INTERVAL)
    async def update_roles(self):
        """
        Check if it's time to add or remove the gotosleep role.
        """
        try:
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
                    if role in member.roles:
                        log.info(f'Removing role from {member} in {guild}.')
                        await member.remove_roles(role)
                    continue

                if self._is_time_inbetween(datetime.datetime.now().time(), start, end):
                    if role not in member.roles:
                        log.info(f'Adding role to {member} in {guild}.')
                        await member.add_roles(role)
                else:
                    if role in member.roles:
                        log.info(f'Removing role from {member} in {guild}.')
                        await member.remove_roles(role)
        except Exception as e:
            log.error(f'Error in gotosleep update_roles: {e}')
            log.error(f'Related Record: {record}')

    async def _set_up_role_and_channel_permissions_if_needed(self, guild: discord.Guild) -> None:
        """ Create the gotosleep role and set permission override for all existing channels. """

        # create role if it doesn't exist
        if not (gotosleep_role := self._get_gotosleep_role(guild)):
            try:
                await guild.create_role(name=GOTOSLEEP_ROLE_NAME)
                log.info(f'Created gotosleep role in {guild}')
            except Exception as e:
                log.error(f'Failed to create gotosleep role in {guild}: {e}')
                return
            
        # set permissions if channel doesn't have it
        for channel in guild.channels:
            # if gotosleep can view this channel, set it to false
            if channel.permissions_for(gotosleep_role).view_channel:
                try:
                    log.info(f'Setting permissions for {channel} in {guild}')
                    await channel.set_permissions(gotosleep_role, view_channel=False)
                except Exception as e:
                    log.error(f'Failed to set permissions for {channel} in {guild}: {e}')
                    return
                
    @update_roles.before_loop
    async def before_update_roles(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self._set_up_role_and_channel_permissions_if_needed(guild)
        log.info("Starting gotosleep role update loop")

    @update_roles.after_loop
    async def after_update_roles(self):
        log.info("Stopping gotosleep role update loop")

    @commands.command()
    @commands.is_owner()
    async def forcesetup(self, ctx: commands.Context, guild_id: int):
        """ Force setup for a guild. """
        guild = self.bot.get_guild(guild_id)
        await self._set_up_role_and_channel_permissions_if_needed(guild)
        await ctx.send('Done.')
