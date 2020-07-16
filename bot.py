from cogs import webserver
from discord.ext import commands
import discord
import logging.config
from pathlib import Path
import yaml
import os

bot = commands.Bot(command_prefix='z!')

LOGS_DIRECTORY = 'data/logs/'

extensions = [
    'cogs.misc',
    'cogs.tagging',
    'cogs.twitcasting'
]


@bot.event
async def on_command_error(ctx, error):
    if hasattr(ctx.command, "on_error"):
        return

    if ctx.cog:
        if commands.Cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
            return

    logger.warning('%s - %s', ctx.message.content, error)
    await ctx.send(f"{error}\nType `z!help` for usage details.")


@bot.event
async def on_ready():
    logger.info('Logged in as: %s', bot.user)
    logger.info('Discord.py version: %s', discord.__version__)


@bot.event
async def on_message(message):
    await bot.process_commands(message)

if __name__ == '__main__':
    Path(LOGS_DIRECTORY).mkdir(parents=True, exist_ok=True)
    with open('logging.conf.yaml', 'rt') as f:
        config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)

    logger = logging.getLogger('zhenpai')

    for ext in extensions:
        bot.load_extension(ext)
        logger.info('Loaded extension: %s', ext)

    webserver.start_server()

if os.environ.get('DISCORD_BOT_TOKEN'):
    bot.run(os.environ['DISCORD_BOT_TOKEN'])
else:
    import config
    bot.run(config.bot_token)
