import logging
import discord
import datetime
from bot import Zhenpai
from discord.ext import commands, tasks

log: logging.Logger = logging.getLogger(__name__)

NINE_AM_CENTRAL = datetime.time(hour=9, minute=0, tzinfo=datetime.timezone(datetime.timedelta(hours=-6)))
SATURDAY_WEEKDAY = 5
IMAGE_NAME = './cogs/saturday/Saturday.jpg'
USER_ID = 118956121913425920

class Saturday(commands.Cog):
    """
    To remind us to do good things on Saturday.
    """
    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.my_task.start()

    def cog_unload(self):
        self.my_task.cancel()

    # checks everyday at 9am Central Time
    @tasks.loop(time=NINE_AM_CENTRAL)
    async def my_task(self):
        # check if today is Saturday
        if datetime.date.weekday() == SATURDAY_WEEKDAY:
            dm_channel = self.bot.get_user(USER_ID)
            await dm_channel.send(file=discord.File(IMAGE_NAME))

    @my_task.before_loop
    async def before_my_task(self):
        await self.bot.wait_until_ready()
        log.info(f"Starting {__name__} update loop")

    @my_task.after_loop
    async def after_my_task(self):
        log.info(f"Stopping {__name__} update loop")