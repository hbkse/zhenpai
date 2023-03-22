from discord.ext import commands
import discord
import logging
import config
from aiohttp import ClientSession

from typing import Optional

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
    def __init__(self, 
        http_client: ClientSession, 
        testing_guild_id: Optional[int] = None
    ):
        super().__init__(
            command_prefix=config.COMMAND_PREFIX, 
            owner_id=config.OWNER_ID, 
            intents=setup_intents()
        )
        self.http_client = http_client
        self.testing_guild_id = testing_guild_id or config.TESTING_GUILD_ID

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

    async def setup_hook(self) -> None:
        for ext in extensions:
            await self.load_extension(ext)
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