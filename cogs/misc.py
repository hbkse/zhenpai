import random
from typing import Optional, List
import discord
import datetime
import pytz
import time
import parsedatetime as pdt
from discord.ext import commands
from bot import Zhenpai

import logging

log: logging.Logger = logging.getLogger(__name__)

class Misc(commands.Cog):
    """Miscellaneous commands."""

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.pdtcal = pdt.Calendar()

    @commands.command()
    async def ping(self, ctx: commands.Context):
        await ctx.send('pong')

    @commands.command()
    async def echo(self, ctx: commands.Context, content):
        await ctx.send(content)

    @commands.command()
    async def asaman(self, ctx: commands.Context, remove: Optional[int] = 0):
        if ctx.message.reference and (reply_msg := ctx.message.reference.resolved):
            prev_message = reply_msg
        else:
            prev_message = [message async for message in ctx.channel.history(limit=2)][1]
        content = ' '.join(prev_message.content.split(" ")[remove:])
        out = f"why are you, as a man, {content}"
        await ctx.send(out)

    @commands.command()
    async def timeout(self, ctx: commands.Context, minutes: int = 1):
        """ Time yourself out. For your own good. """
        if minutes > 1440:
            await ctx.send("You can't time yourself out for more than 1440 minutes (24 hours). Just to be safe.")
            return
        await ctx.author.timeout(datetime.timedelta(minutes=minutes))
        await ctx.send(f"Bye bye :wave:")

    @commands.command()
    async def deletelast(self, ctx: commands.Context, n: int):
        if n < 1:
            await ctx.send("Please provide a valid number greater than 0.")
            return

        if n > 100:
            await ctx.send("bruh aint no way you tryna delete that much sounds kinda sus do it in batches of 100 so you dont wipe the entire channel")
            return

        messages = []
        async for message in ctx.channel.history(limit=n + 1):
            messages.append(message)

        await ctx.channel.delete_messages(messages)

    @commands.command()
    async def roll(self, ctx: commands.Context, n: int = 100):
        roll = random.randint(1, n)
        if roll == 1:
            await ctx.send(f'🎲 {ctx.author.display_name} rolled a {roll}! Get Fucked!')
        else:
            await ctx.send(f'🎲 {ctx.author.display_name} rolled a {roll}!')

    @commands.command()
    async def vietnam(self, ctx: commands.Context):
        """
        Get the current time in Vietnam
        """
        await self._get_timezone_time(ctx, 'Asia/Ho_Chi_Minh', 'Vietnam')

    @commands.command()
    async def india(self, ctx: commands.Context):
        """
        Get the current time in India
        """
        await self._get_timezone_time(ctx, 'Asia/Kolkata', 'India')

    @commands.command()
    async def japan(self, ctx: commands.Context):
        """
        Get the current time in Japan
        """
        await self._get_timezone_time(ctx, 'Asia/Tokyo', 'Japan')

    async def _get_timezone_time(self, ctx: commands.Context, timezone_name: str, country_name: str):
        """Helper method to get and display current time in a specific timezone"""
        timezone = pytz.timezone(timezone_name)
        current_time = datetime.datetime.now(timezone)
        formatted_time = current_time.strftime('%m-%d %H:%M:%S')
        await ctx.send(f'The current datetime in {country_name} is: {formatted_time}')

    @commands.command()
    async def ben(self, ctx: commands.Context, *, content: str):
        """
        determines if ben is working or not given a day in the future
        """
        def is_ben_working(content: str):
            """
            returns (bool, str) where str is the explanation string
            """
            start_date_str = "November 4, 2024" # arbitrary start date where he's working

            # Parse dates
            input_struct, parse_status = self.pdtcal.parse(content)
            if parse_status == 0:
                return False, f"Could not parse input date: {content}"
            input_date = datetime.datetime.fromtimestamp(time.mktime(input_struct))
            start_struct, _ = self.pdtcal.parse(start_date_str)
            start_date = datetime.datetime.fromtimestamp(time.mktime(start_struct))
            
            # Calculate days since start date (can be negative for past dates)
            days_diff = (input_date - start_date).days
            cycle_day = days_diff % 14
            
            # First 7 days (0-6) are working days, next 7 (7-13) are off days
            is_working = cycle_day < 7
            
            # Create explanation message
            date_str = input_date.strftime("%A, %B %d, %Y")
            status = "working" if is_working else "off"
            
            explanation = f"On {date_str}, they are {status}. "

            if cycle_day == 13:
                explanation += "But, this is their last day off (Sunday) before returning to work."
            
            return is_working, explanation
        is_working, message = is_ben_working(content)
        await ctx.send(message)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # await self._call_and_response(message, "based", ["based on", "based off"], "on what?")
        await self._call_and_response(message, "buy the dip", ["buy the dip with"], "with what?")

    async def _call_and_response(self, message: discord.Message, target: str, exclusions: List[str], response: str):
        """Send `response` when `target` phrase exists and no exclusion matches."""
        def _has_phrase(words: List[str], phrase: List[str]) -> bool:
            n = len(phrase)
            return any(words[i:i + n] == phrase for i in range(len(words) - n + 1))

        words = message.content.lower().split()
        if not _has_phrase(words, target.lower().split()):
            return
        if any(_has_phrase(words, ex.lower().split()) for ex in exclusions):
            return

        await message.channel.send(response)

async def setup(bot: Zhenpai):
    await bot.add_cog(Misc(bot))