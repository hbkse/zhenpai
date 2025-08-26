from discord.ext import commands
import discord
import logging
import config
from aiohttp import ClientSession
import asyncpg
import datetime

from typing import Optional

log: logging.Logger = logging.getLogger(__name__)

extensions_dir = "cogs.{}"
extensions = [
    'misc',
    'tags',
    # 'spotify',
    'remindme',
    'reposts',
    # 'gotosleep',
    'apex',
    'wow',
    'admin',
    # 'vxtwitter',
    'saturday',
    'cs2',
]

def setup_intents():
    intents = discord.Intents.default()
    intents.presences = True
    intents.members = True
    intents.message_content = True
    return intents

class Zhenpai(commands.Bot):
    def __init__(self, 
        http_client: ClientSession, 
        db_pool: asyncpg.pool,
        testing_guild_id: Optional[int] = None
    ):
        super().__init__(
            command_prefix=config.COMMAND_PREFIX, 
            owner_id=config.OWNER_ID, 
            intents=setup_intents()
        )
        self.http_client = http_client
        self.db_pool = db_pool
        self.testing_guild_id = testing_guild_id or config.TESTING_GUILD_ID
        self.start_time = datetime.datetime.now()

    async def on_ready(self):
        log.info('Logged in as: %s', self.user)
        log.info('Discord.py version: %s', discord.__version__)
        log.info('Commit hash: %s', config.COMMIT_HASH)

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
        elif isinstance(error, commands.BotMissingPermissions):
            return await ctx.send('I don\'t have permissions in this server to do that.')
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.errors.Forbidden):
            return await ctx.send('I don\'t have permissions in this server to do that (probably).')
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, ValueError):
            return await ctx.send('Something wrong with the command arguments (probably).')
        elif hasattr(ctx.command, "on_error"):
            return

        if ctx.cog:
            if commands.Cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
                return

        log.warning('%s - %s - %s', ctx.message.content, error, type(error))
    
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        await self.process_commands(message)

    async def setup_hook(self) -> None:
        for ext in extensions:
            await self.load_extension(extensions_dir.format(ext))
            log.info('Loaded extension: %s', ext)
        
        # Sync app_commands for testing guild
        if self.testing_guild_id:
            log.info(f'Syncing global commands to {self.testing_guild_id}')
            guild = discord.Object(self.testing_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info(f'Finished syncing global commands')

        # This would also be a good place to connect to our database and
        # load anything that should be in memory prior to handling events.

    async def _run(self):
        await self.start(config.DISCORD_BOT_TOKEN)