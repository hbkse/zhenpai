import discord
from discord.ext import commands
import config
import logging

bot = commands.Bot(command_prefix='z!')

extensions = [
    'cogs.misc',
    'cogs.tagging'
]


@bot.event
async def on_ready():
    print('Logged in as: ', bot.user)
    print('Discord.py version: ', discord.__version__)


@bot.event
async def on_message(message):
    await bot.process_commands(message)

if __name__ == '__main__':
    logger = logging.getLogger('zhenpai')
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(fmt='[%(asctime)s] %(name)s: %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    for ext in extensions:
        bot.load_extension(ext)
        logger.debug('Loaded extension: %s', ext)

bot.run(config.bot_token)
