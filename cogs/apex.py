from discord.ext import commands
import logging
import datetime

log: logging.Logger = logging.getLogger(__name__)

SEASON_16_RANKED_MAPS = ["World's Edge", "Storm Point", "Broken Moon"]
SEASON_16_END_DATES = []
START_DATE = datetime.datetime(2023, 3, 19, 13 + 5, tzinfo=datetime.timezone.utc) # 3/19 1PM UTC+5, WORLD'S EDGE
SEASON_16_SPLIT_1_END_DATE = datetime.datetime(2023, 4, 4, 13 + 5, tzinfo=datetime.timezone.utc) # 4/4 1PM UTC+5

class Apex(commands.Cog):
    """Commands for Apex Legends"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    async def map(self, ctx: commands.Context):
        time_passed =  datetime.datetime.now(datetime.timezone.utc) - START_DATE
        index = time_passed.days % 3
        await ctx.send(f"Current ranked map: {SEASON_16_RANKED_MAPS[index]}")

    @commands.command()
    async def split(self, ctx: commands.Context):
        time_remaining =  datetime.datetime.now(datetime.timezone.utc) - SEASON_16_SPLIT_1_END_DATE
        days = time_remaining.days or 0
        hours = time_remaining.seconds // 3600
        await ctx.send(f"Current ranked split ends in: {days} days {hours} hours")

async def setup(bot):
    await bot.add_cog(Apex(bot))