import logging

import discord
import datetime
from discord.ext import tasks, commands
from bot import Zhenpai
from .db import ReminderDb

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

    @commands.command()
    async def remindme(self, ctx: commands.Context, time: str, *, message: str):
        """Remind me to do something in the future."""
        await ctx.send(f"uhh, I'll finish this later.", ephemeral=True)

        # converted_time = self._convert_time(time)
        # await self.db.add_reminder(ctx, converted_time, message)
        # await ctx.send(f"Ok, I'll remind you to {message} at {converted_time}.", ephemeral=True)
    
    @tasks.loop(minutes=REMINDER_LOOP_MINUTES)
    async def check_reminders(self):
        """ Check for reminders that need to be sent. """

        reminders = await self.db.get_reminders_ordered()
        for reminder in reminders:
            if reminder['remind_time'] < datetime.datetime.now():
                user = self.bot.get_user(reminder['user_id'])
                if user:
                    log.info(f"Sending reminder to {reminder['user_id']}: {reminder['content']}")
                    await user.send(f"You told me to remind you: {reminder['content']}")
                    log.info(f"Deleting reminder {reminder['id']}")
                    await self.db.delete_reminder(reminder['id'])
                else:
                    log.error(f"Could not find user {reminder['user_id']} to send reminder to.")

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()
        log.info("Starting remindme update loop")

    @check_reminders.after_loop
    async def after_check_reminders(self):
        log.info("Stopping remindme update loop")