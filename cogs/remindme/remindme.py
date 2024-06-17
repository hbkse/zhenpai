import logging

import discord
from discord.ext import tasks, commands
from datetime import datetime, timezone
import pytz
import parsedatetime as pdt

from bot import Zhenpai
from .db import ReminderDb

log: logging.Logger = logging.getLogger(__name__)

REMINDER_LOOP_MINUTES = 1

central = pytz.timezone('US/Central')

class RemindMe(commands.Cog):
    """ Remind me to do something in the future. """

    def __init__(self, bot: Zhenpai):
        self.bot = bot  
        self.db = ReminderDb(self.bot.db_pool)
        self.check_reminders.start()
        self.datetime_parser = pdt.Calendar()

    def cog_unload(self):
        self.check_reminders.cancel()

    def _convert_time(self, time: str, timezone=None) -> datetime:
        """ Convert time string to datetime object. 
            Returns: UTC-0 datetime or None if parsing failed
        """

        # discord doesnt have any way to exposing a user's timezone, so relative times are kinda awkward
        # here I just always assume user is in central timezone
        timezone = central if not timezone else timezone
        timezone_adjusted_next_time, parse_status = self.datetime_parser.parseDT(time, datetime.now(timezone))

        # return as utc
        return timezone_adjusted_next_time.astimezone(pytz.utc) if parse_status else None
        
        
    @commands.command(hidden=True)
    async def testdateparse(self, ctx: commands.Context, *, time: str):
        """ Test date parsing. """
        remind_time = self._convert_time(time)
        await ctx.send(f"parsed time: {remind_time}   utc now: {datetime.now(pytz.utc)}    central now: {datetime.now(central)}")

    @commands.command(hidden=True)
    async def remind(self, ctx: commands.Context, target: str, *, message: str):
        """ Command alias for remindme and remindus """
        if target == "me":
            await self._remind_command_impl(ctx, message, is_private=True)
        elif target == "us":
            await self._remind_command_impl(ctx, message, is_private=False)

    @commands.command(name="remindme")
    async def remind_me(self, ctx: commands.Context, *, message: str):
        """Remind me to do something in the future. It will DM the user who issued the command. 
        
        Usage: !remindme <when> to <what>

        Example: !remindme in 1 hour to check the oven
        """
    
        await self._remind_command_impl(ctx, message, is_private=True)
    
    @commands.command(name="remindus")
    async def remind_us(self, ctx: commands.Context, *, message: str):
        """Remind us to do something in the future. It will post in the channel where the command was issued. 
        
        Usage: !remindus <when> to <what>

        Example: !remindus in 1 hour to check the oven
        """

        await self._remind_command_impl(ctx, message, is_private=False)

    async def _remind_command_impl(self, ctx: commands.Context, message: str, is_private: bool):
        # im dumb and stubborn for not wanting this as a slash command, argument parsing here is bad
        # also you get the ephemeral response with slash commands

        to_split = message.split(" to ", 1)
        if len(to_split) != 2:
            await ctx.send("I couldn't understand. This command expects \" to \" to exactly separate the time and message, like \"!remind me tomorrow to check the mail\" :smile:")
            return
        time_phrase, remind_message = to_split[0], to_split[1] 

        remind_time = self._convert_time(time_phrase)
        if not remind_time:
            await ctx.send(f"I couldn't understand the time you entered: {time_phrase}")
            return

        # check result? or do exception handling?
        res = await self.db.add_reminder(ctx, remind_time, remind_message, is_private)
        await ctx.message.add_reaction("✅")
    
    # @commands.command()
    async def get_my_reminders(self, ctx: commands.Context):
        """ Get all reminders for the user who issued the command. """
        # remember to display to user in their timezone
        await ctx.send("havent implemented this yet")

    # @commands.command()
    async def delete_my_reminder(self, ctx: commands.Context, reminder_id: int):
        """ Delete a reminder for the user who issued the command. """
        await ctx.send("havent implemented this yet")
    
    @tasks.loop(minutes=REMINDER_LOOP_MINUTES)
    async def check_reminders(self):
        """Polling loop that checks if any reminders need to be sent."""

        active_reminders = await self.db.get_active_reminders()
        for reminder in active_reminders:
            log.info(f"Trying to send reminder id: {reminder.id}")
            if reminder.is_private:
                user = self.bot.get_user(reminder.user_id) # handle null user?
                await user.send(f"You told me to remind you: {reminder.content}")
            else:
                channel = self.bot.get_channel(reminder.channel_id) # handle null channel?
                # assert guild channel? 
                await channel.send(f"You told me to remind everyone: {reminder.content}")
            await self.db.mark_reminder_sent(reminder.id)

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()
        log.info(f"Starting {__name__} update loop")

    @check_reminders.after_loop
    async def after_check_reminders(self):
        log.info(f"Stopping {__name__} update loop")