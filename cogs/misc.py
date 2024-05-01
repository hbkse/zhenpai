import random
from typing import Optional
import discord
import datetime
import pytz
from discord.ext import commands
from bot import Zhenpai
import logging

log: logging.Logger = logging.getLogger(__name__)

class Misc(commands.Cog):
    """Miscellaneous commands."""

    def __init__(self, bot: Zhenpai):
        self.bot = bot

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
    async def deletelast(self, ctx, n: int):
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
    async def roll(self, ctx, n: int = 100):
        roll = random.randint(1, n)
        if roll == 1:
            await ctx.send(f'🎲 {ctx.author.display_name} rolled a {roll}! Get Fucked!')
        else:
            await ctx.send(f'🎲 {ctx.author.display_name} rolled a {roll}!')

    @commands.command()
    async def india(self, ctx):
        """
        gives you the current time in india elelelelele
        """
        india_timezone = pytz.timezone('Asia/Kolkata')
        india_time = datetime.datetime.now(india_timezone)
        formatted_time = india_time.strftime('%Y-%m-%d %H:%M:%S')
        await ctx.send(f'The current time in India is: {formatted_time}')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # based? on what?
        based = "based"
        not_based = ["on", "off"]
        words = message.content.lower().split(" ")
        
        should_send_message = False
        if based in words:
            should_send_message = True
            i = words.index(based)
            if i + 1 < len(words):
                next_word = words[i + 1]
                if next_word in not_based:
                    should_send_message = False

        if should_send_message:
            await message.channel.send("on what?")


async def setup(bot: Zhenpai):
    await bot.add_cog(Misc(bot))