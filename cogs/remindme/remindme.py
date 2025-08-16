import logging

import discord
from discord.ext import tasks, commands
from datetime import datetime, timezone
import pytz
import parsedatetime as pdt

from bot import Zhenpai
from .db import ReminderDb
from .types import ReminderType

log: logging.Logger = logging.getLogger(__name__)

REMINDER_LOOP_MINUTES = 1

CENTRAL_TIMEZONE = pytz.timezone('US/Central')

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
        user_timezone = CENTRAL_TIMEZONE if not timezone else timezone
        user_timezone_naive_next_time, parse_status = self.datetime_parser.parseDT(time, sourceTime=datetime.now(user_timezone))
        if not parse_status:
            return None

        log.info(f"user_timezone_naive_next_time: {user_timezone_naive_next_time}")
        user_timezone_aware_next_time = user_timezone.localize(user_timezone_naive_next_time)
        log.info(f"user_timezone_aware_next_time: {user_timezone_aware_next_time}")
        utc_aware_next_time = user_timezone_aware_next_time.astimezone(pytz.utc)
        log.info(f"utc_aware_next_time: {utc_aware_next_time}")
        utc_naive_next_time = utc_aware_next_time.replace(tzinfo=None)
        log.info(f"utc_naive_next_time: {utc_naive_next_time}")
        return utc_naive_next_time
        
    @commands.command(aliases=['tdp'], hidden=True)
    async def testdateparse(self, ctx: commands.Context, *, time: str):
        """ Test date parsing. """
        remind_time = self._convert_time(time)
        await ctx.send(f"parsed time: {remind_time}   utc now: {datetime.now(pytz.utc)}    central now: {datetime.now(CENTRAL_TIMEZONE)}")

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
        Special: Add "in this chat" or "in this channel" to post the reminder in the channel and mention you.

        Example: !remindme in 1 hour to check the oven
        Example: !remindme in 1 hour to check the oven in this chat
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

        # Check for "in this chat" or "in this channel" phrases
        in_chat_phrases = ["in this chat", "in this channel"]
        reminder_type = ReminderType.PRIVATE if is_private else ReminderType.PUBLIC
        
        # Remove the chat/channel phrases from the message for parsing
        original_message = message
        for phrase in in_chat_phrases:
            if phrase in message.lower():
                message = message.replace(phrase, "").strip()
                if is_private:  # Only allow "in this chat" for remindme commands
                    reminder_type = ReminderType.MENTION
                break

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
        res = await self.db.add_reminder(ctx, remind_time, remind_message, reminder_type)
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
            
            try:
                if reminder.reminder_type == ReminderType.PRIVATE:
                    user = self.bot.get_user(reminder.user_id)
                    if user:
                        await user.send(f"You told me to remind you: {reminder.content}")
                    else:
                        log.warning(f"Could not find user {reminder.user_id} for reminder {reminder.id}")
                elif reminder.reminder_type == ReminderType.PUBLIC:
                    channel = self.bot.get_channel(reminder.channel_id)
                    if channel:
                        await channel.send(f"You told me to remind everyone: {reminder.content}")
                    else:
                        log.warning(f"Could not find channel {reminder.channel_id} for reminder {reminder.id}")
                elif reminder.reminder_type == ReminderType.MENTION:
                    channel = self.bot.get_channel(reminder.channel_id)
                    user = self.bot.get_user(reminder.user_id)
                    if channel and user:
                        await channel.send(f"{user.mention} You told me to remind you: {reminder.content}")
                    else:
                        log.warning(f"Could not find channel {reminder.channel_id} or user {reminder.user_id} for reminder {reminder.id}")
                else:
                    log.error(f"Unknown reminder type: {reminder.reminder_type} for reminder {reminder.id}")
                    continue
                    
                await self.db.mark_reminder_sent(reminder.id)
            except Exception as e:
                log.error(f"Error sending reminder {reminder.id}: {e}")
                continue

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()
        log.info(f"Starting {__name__} update loop")

    @check_reminders.after_loop
    async def after_check_reminders(self):
        log.info(f"Stopping {__name__} update loop")