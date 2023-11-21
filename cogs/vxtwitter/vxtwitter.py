import random
from typing import Optional
from bot import Zhenpai

import discord
from discord import app_commands
from discord.ext import tasks, commands
import logging
import datetime
import re

log: logging.Logger = logging.getLogger(__name__)

class VxTwitter(commands.Cog):
    """ For handling twitter links """

    def __init__(self, bot: Zhenpai):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # todo, update this to like "findall" and then "for each match, concat/send message"
        regex_pattern = re.compile(r'https://(?:twitter|x)\.com/(\w+)/status/(\d+)')
        match = regex_pattern.search(message.content)
        
        if match:
            username, tweet_id = match.groups()
            new_link = f'https://vxtwitter.com/{username}/status/{tweet_id}'
            await message.channel.send(new_link)
            