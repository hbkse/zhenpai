import logging

import discord
import datetime
from discord.ext import tasks, commands
from bot import Zhenpai
from .db import ReminderDb
from .db import Reminder

log: logging.Logger = logging.getLogger(__name__)

REMINDER_LOOP_MINUTES = 1

class RemindMe(commands.Cog):
    """ Remind me to do something in the future. """

    def __init__(self, bot: Zhenpai):
        self.bot = bot  
        self.db = ReminderDb(self.bot.db_pool)
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    def _convert_time(self, time: str) -> datetime.datetime:
        """ Convert time string to datetime object. """

        # +30 minutes for now
        return datetime.datetime.now() + datetime.timedelta(minutes=30)
        # TODO:
        # parse relative times (in 6 minutes, in 1 hour, etc.)
        # parse absolute times (at 6:00, 6:00pm, etc.)

    @commands.command(hidden=True)
    async def remind(self, ctx: commands.Context, target: str, time: str, *, message: str):
        """ Command alias for remindme and remindus """
        if target == "me":
            await self.remind_me(ctx, time, message)
        elif target == "us":
            await self.remind_us(ctx, time, message)

    @commands.command(name="remindme")
    async def remind_me(self, ctx: commands.Context, time: str, *, message: str):
        """Remind me to do something in the future. It will DM the user who issued the command. 
        
        Usage: !remindme <time> <message>
        """

        # this command is so much better as a slash command
        pass
    
    @commands.command(name="remindus")
    async def remind_us(self, ctx: commands.Context, time: str, *, message: str):
        """Remind us to do something in the future. It will post in the channel where the command was issued. 
        
        Usage: !remindus <time> <message>
        """

        pass
    
    @tasks.loop(minutes=REMINDER_LOOP_MINUTES)
    async def check_reminders(self):
        """Polling loop that checks if any reminders need to be sent."""

        active_reminders = await self.db.get_active_reminders()
        for reminder in active_reminders:
            log.info(f"Trying to send reminder {reminder.id}")
            if reminder.is_private:
                user = self.bot.get_user(reminder.user_id) # handle null user?
                await user.send(f"{reminder.content}")
            else:
                channel = self.bot.get_channel(reminder.channel_id) # handle null channel?
                # assert guild channel? 
                await channel.send(f"{reminder.content}")
            await self.db.mark_reminder_sent(reminder.id)

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()
        log.info(f"Starting {__name__} update loop")

    @check_reminders.after_loop
    async def after_check_reminders(self):
        log.info(f"Stopping {__name__} update loop")