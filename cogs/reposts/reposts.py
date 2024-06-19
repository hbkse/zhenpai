import logging

import discord
import re
from discord.ext import commands
from bot import Zhenpai
from ..helpers import TTLCache

log: logging.Logger = logging.getLogger(__name__)

TWITTER_PATTERN = r"(https?://(?:www\.)?twitter\.com/[\w-]+/status/[\w-]+)"
X_PATTERN = r"(https?://(?:www\.)?x\.com/[\w-]+/status/[\w-]+)"
YOUTUBE_PATTERN = r"(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+)"
REDDIT_PATTERN = r"(https?://(?:www\.)?reddit\.com/r/[\w-]+/comments/[\w-]+/[\w-]+)"

class Reposts(commands.Cog):
    """ Leaves a raised eyebrow react on messages that are recent reposts. """

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        # this is just in memory, one day could persist this
        self.cache = TTLCache.TTLCache(ttl_seconds=3 * 24 * 60 * 60) # 3 days ttl

    def _build_cache_key(self, channel_id: str, link: str) -> str:
        return f"{channel_id}:{link}"
    
    @commands.command(hidden=True)
    async def debug_cache(self, ctx: commands.Context):
        await ctx.send(f"size: {len(self.cache.cache)} Cache: {self.cache.cache}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        if message.content:
            matches = [re.findall(pattern, message.content) for pattern in [YOUTUBE_PATTERN, REDDIT_PATTERN, TWITTER_PATTERN, X_PATTERN]]
            flattened_matches = [match for sublist in matches for match in sublist]
            should_react = False
            for match in flattened_matches:
                if not match:
                    continue
                cache_key = self._build_cache_key(message.channel.id, match)
                if cache_key in self.cache:
                    should_react = True
                
                res = self.cache[cache_key] = True
                if not res:
                    log.info(f"Failed to set cache key: {cache_key}")
            if should_react:
                await message.add_reaction("🤨")
                return
                