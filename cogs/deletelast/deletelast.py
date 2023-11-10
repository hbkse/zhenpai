import logging

import discord
from discord.ext import commands
from bot import Zhenpai

log: logging.Logger = logging.getLogger(__name__)

class DeleteLast(commands.Cog):
    """ Purge the last N messages to repent sins. """

    def __init__(self, bot: Zhenpai):
        self.bot = bot

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
