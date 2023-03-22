from discord.ext import commands
import discord
import logging
import config
from aiohttp import ClientSession

log: logging.Logger = logging.getLogger(__name__)

extensions = [
    'cogs.misc',
    # 'cogs.tagging',
    # 'cogs.spotify',
    'cogs.gotosleep',
    'cogs.apex',
    'cogs.admin'
]

def setup_intents():
    intents = discord.Intents.default()
    intents.presences = True
    intents.members = True
    intents.message_content = True
    return intents

class Zhenpai(commands.Bot):
    def __init__(self, http_client: ClientSession):
        super().__init__(
            command_prefix=config.COMMAND_PREFIX, 
            owner_id=config.OWNER_ID, 
            intents=setup_intents()
        )
        self.http_client = http_client

    async def on_ready(self):
        log.info('Logged in as: %s', self.user)
        log.info('Discord.py version: %s', discord.__version__)

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.NotOwner):
            return
        elif isinstance(error, commands.CheckAnyFailure) or isinstance(error, commands.CheckFailure):
            return await ctx.send(error)
        elif isinstance(error, commands.TooManyArguments):
            return await ctx.send('Too many argument(s).')
        elif isinstance(error, commands.BadArgument):
            return await ctx.send('Invalid argument(s).')
        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send('Missing argument(s).')
        elif hasattr(ctx.command, "on_error"):
            return

        if ctx.cog:
            if commands.Cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
                return

        log.warning('%s - %s', ctx.message.content, error)
    
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        await self.process_commands(message)

    async def _run(self):
        for ext in extensions:
            await self.load_extension(ext)
            log.info('Loaded extension: %s', ext)
        await self.start(config.DISCORD_BOT_TOKEN)