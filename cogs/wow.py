from discord.ext import commands
import logging
import datetime

import pytz
import config
from bot import Zhenpai

log: logging.Logger = logging.getLogger(__name__)

class Wow(commands.Cog):
    """Commands for world of warcraft"""

    def __init__(self, bot: Zhenpai):
        self.bot = bot

    @commands.command()
    async def wowtoken(self, ctx: commands.Context):
        """Get the current price of a WoW token"""
        async with self.bot.http_client.get("https://data.wowtoken.app/token/current.json") as resp:
            if resp.status == 200:
                data = await resp.json()
                current_time = data['current_time']
                price_data = data['price_data']
                update_times = data['update_times']

                us_price = price_data['us']
                us_iso_time = update_times['us']
                readable_time = datetime.datetime.fromisoformat(us_iso_time).astimezone(pytz.timezone("America/Chicago")).strftime("%Y-%m-%d %I:%M:%S %p %Z")

                await ctx.send(f"WoW token is **{us_price}**. Last updated at {readable_time}")

async def setup(bot: Zhenpai):
    await bot.add_cog(Wow(bot))