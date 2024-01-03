import random
from typing import Optional
import discord
import datetime
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
        flavor = ''

        if roll == 1:
            if n < 20:
                flavor = 'Get Fucked!'
            else:
                flavor = 'GET FUCKED!!'
        
        await ctx.send(f'🎲 {ctx.author.nick} rolled a {roll}! {flavor}')

async def setup(bot: Zhenpai):
    await bot.add_cog(Misc(bot))