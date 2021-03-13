import discord
from discord.ext import commands

from database import DB


class Reminders(commands.Cog):
    """"""

    def __init__(self, bot):
        self.bot = bot
        self.db = DB

    @commands.command(aliases=["remindme"])
    async def remind(self, ctx, ):
        # z!remindme [time] [subject]
        # z!remindme [in 5 minutes] [to wash the dishes]
        # z!remindme [int] [string]


def setup(bot):
    bot.add_cog(Reminders(bot))
