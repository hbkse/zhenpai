import logging
from discord.ext import commands

from database import DB
from .twitcasting import Twitcasting


class Notifications(Twitcasting):
    def __init__(self, bot):
        self.logger = logging.getLogger('zhenpai.notifications')
        self.bot = bot
        self.db = DB
        Twitcasting.__init__(self)

    @commands.group()
    async def ntfy(self, ctx):
        if ctx.invoked_subcommand is None:
            help_text = ""
            for command in self.walk_commands():
                if command is not self.ntfy and isinstance(command, commands.Group):
                    help_text += f'{command}: {command.help}\n'
            await ctx.send(f'```{help_text}```')
