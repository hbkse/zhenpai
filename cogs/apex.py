from discord.ext import commands
import logging
import datetime
import config
from bot import Zhenpai

log: logging.Logger = logging.getLogger(__name__)


# SEASON_16_RANKED_MAPS = ["**World's Edge** 🏙️🔥", "**Storm Point** ⛱️🐺", "**Broken Moon** 💩🌙"]
# SEASON_16_RANKED_MAPS = ["**Olympus** 🌌🔬", "**Storm Point** ⛱️🐺", "**Broken Moon** 💩🌙"]
# SEASON_17_RANKED_MAPS = ["**Olympus** 🌌🔬", "**King's Canyon** 💩💩", "**World's Edge** 🏙️🔥"]
# SEASON_18_RANKED_MAPS = ["**Broken Moon** 💩🌙", "**King's Canyon** 💩💩", "**Olympus** 🌌🔬"]
# SEASON_19_RANKED_MAPS = ["**Storm Point** ⛱️🐺", "**Broken Moon** 💩🌙", "**Olympus** 🌌🔬"]
# SEASON_20_RANKED_MAPS = ["**Olympus** 🌌🔬", "**Storm Point** ⛱️🐺", "**World's Edge** 🏙️🔥"]
# SEASON_20_RANKED_MAPS = ["**Storm Point** ⛱️🐺", "**Olympus** 🌌🔬", "**World's Edge** 🏙️🔥"]
SEASON_21_RANKED_MAPS = ["**Broken Moon** 💩🌙", "**World's Edge** 🏙️🔥", "**King's Canyon** 💩💩"]
# START_DATE = datetime.datetime(2023, 3, 19, 13 + 5, tzinfo=datetime.timezone.utc) # 3/19 1PM UTC+5, WORLD'S EDGE
# SEASON_16_SPLIT_1_END_DATE = datetime.datetime(2023, 4, 4, 13 + 5, tzinfo=datetime.timezone.utc) # 4/4 1PM UTC+5
# SEASON_16_SPLIT_2_END_DATE = datetime.datetime(2023, 5, 9, 13 + 5, tzinfo=datetime.timezone.utc) # 5/9 1PM UTC+5
# SEASON_17_START_DATE = datetime.datetime(2023, 5, 9, 12 + 5, tzinfo=datetime.timezone.utc) # 5/9 1PM UTC+5
# SEASON_17_END_DATE = datetime.datetime(2023, 6, 20, 12 + 5, tzinfo=datetime.timezone.utc) # 6/20 1PM UTC+5
# SEASON_18_START_DATE = datetime.datetime(2023, 8, 8, 12 + 5, tzinfo=datetime.timezone.utc) # 8/8 1PM UTC+5
# SEASON_18_END_DATE = datetime.datetime(2023, 10, 30, 12 + 5, tzinfo=datetime.timezone.utc) # 10/30 1PM UTC+5
# SEASON_19_START_DATE = datetime.datetime(2023, 10, 31, 12 + 5, tzinfo=datetime.timezone.utc) 
# SEASON_19_END_DATE = datetime.datetime(2024, 2, 13, 12 + 5, tzinfo=datetime.timezone.utc)
# SEASON_20_START_DATE = datetime.datetime(2024, 2, 13, 12 + 5, tzinfo=datetime.timezone.utc) 
# SEASON_20_END_DATE = datetime.datetime(2024, 5, 6, 12 + 5, tzinfo=datetime.timezone.utc) # idk when it ends
SEASON_21_START_DATE = datetime.datetime(2024, 5, 7, 12 + 5, tzinfo=datetime.timezone.utc) 
SEASON_21_END_DATE = datetime.datetime(2024, 8, 6, 12 + 5, tzinfo=datetime.timezone.utc) # idk when it ends

class Apex(commands.Cog):
    """Commands for Apex Legends"""

    def __init__(self, bot: Zhenpai):
        self.bot = bot

    @commands.command()
    async def map(self, ctx: commands.Context):
        if datetime.datetime.now(datetime.timezone.utc) > SEASON_21_END_DATE:
            await ctx.send("season's over, need to update")
            return

        time_passed =  datetime.datetime.now(datetime.timezone.utc) - SEASON_21_START_DATE
        index = time_passed.days % 3
        current_map = SEASON_21_RANKED_MAPS[index]
        next_map = SEASON_21_RANKED_MAPS[(index + 1) % 3]
        TWENTY_FOUR_HOURS_IN_SECONDS = 86400
        total_seconds_remaining = TWENTY_FOUR_HOURS_IN_SECONDS - time_passed.seconds
        hours_remaining = total_seconds_remaining // 3600
        minutes_remaining = (total_seconds_remaining % 3600) // 60
        await ctx.send(f"Current ranked map is {current_map}  for **{hours_remaining} hours {minutes_remaining} minutes**. Next map is {next_map}")

    @commands.command()
    async def split(self, ctx: commands.Context):
        now = datetime.datetime.now(datetime.timezone.utc)

        if now < SEASON_21_END_DATE:
            time_remaining = SEASON_21_END_DATE - now
        else:
            await ctx.send("season's over, need to update")

        days = time_remaining.days or 0
        hours = time_remaining.seconds // 3600
        await ctx.send(f"Current ranked split ends in: **{days} days {hours} hours**")

    # https://tracker.gg/developers/docs/getting-started
    # @commands.command()
    # async def stats(self, ctx: commands.Context, *, username: str):
    #     """Get Apex Legends stats for a player"""
    #     trn_api_key = config.TRN_API_KEY
    #     async with self.bot.http_client.get(f"https://public-api.tracker.gg/v2/apex/standard/profile/origin/{username}", headers={"TRN-Api-Key": trn_api_key}) as resp:
    #         if resp.status == 200:
    #             data = await resp.json()
    #             stats = data['data']['segments'][0]['stats']
    #             await ctx.send(f"**{username}**'s stats:")

async def setup(bot: Zhenpai):
    await bot.add_cog(Apex(bot))