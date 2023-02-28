from cogs import webserver
from discord.ext import commands
import discord
import logging.config
from pathlib import Path
import yaml
import config
import asyncio

extensions = [
    'cogs.misc',
    # 'cogs.tagging',
    # 'cogs.twitcasting',
    # 'cogs.spotify',
    'cogs.go_to_sleep'
]

def setup_intents():
    intents = discord.Intents.default()
    intents.presences = True
    intents.members = True
    intents.message_content = True
    return intents

logger = logging.getLogger('zhenpai')
bot = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=setup_intents(), owner_id=config.OWNER_ID)

@bot.event
async def on_command_error(ctx, error):
    if hasattr(ctx.command, "on_error"):
        return

    if ctx.cog:
        if commands.Cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
            return

    logger.warning('%s - %s', ctx.message.content, error)
    await ctx.send(f"{error}\nType `{config.COMMAND_PREFIX}help` for usage details.")


@bot.event
async def on_ready():
    logger.info('Logged in as: %s', bot.user)
    logger.info('Discord.py version: %s', discord.__version__)
    logger.info('Visible guilds: %s', bot.guilds)


@bot.event
async def on_message(message):
    await bot.process_commands(message)

async def main():
    Path(config.LOGS_DIRECTORY).mkdir(parents=True, exist_ok=True)
    with open('logging.conf.yaml', 'rt') as f:
        logging_config = yaml.safe_load(f.read())
    logging.config.dictConfig(logging_config)

    # webserver.start_server()

    async with bot:
        for ext in extensions:
            await bot.load_extension(ext)
            logger.info('Loaded extension: %s', ext)
        await bot.start(config.DISCORD_BOT_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())