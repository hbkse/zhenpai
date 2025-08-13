from discord.ext import commands
import logging
import datetime
import config
from bot import Zhenpai

log: logging.Logger = logging.getLogger(__name__)

API_URL = "https://api.mozambiquehe.re/maprotation?version=2"

class Apex(commands.Cog):
    """Commands for Apex Legends"""

    def __init__(self, bot: Zhenpai):
        self.bot = bot

    @commands.command()
    async def map(self, ctx: commands.Context):
        api_key = getattr(config, 'APEX_API_KEY', None)
        if not api_key:
            await ctx.send("APEX_API_KEY is not configured.")
            return

        try:
            async with self.bot.http_client.get(API_URL, headers={"Authorization": api_key}) as resp:
                if resp.status != 200:
                    await ctx.send(f"Failed to fetch map rotation (status {resp.status}).")
                    return
                data = await resp.json()
        except Exception as e:
            log.exception("Error fetching Apex map rotation: %s", e)
            await ctx.send("Error fetching map rotation.")
            return

        ranked = (data or {}).get('ranked', {})
        current = ranked.get('current', {})
        next_map_info = ranked.get('next', {})

        current_map_name = current.get('map') or 'Unknown'
        next_map_name = next_map_info.get('map') or 'Unknown'

        remaining_secs = current.get('remainingSecs')
        if remaining_secs is None:
            end_ts = current.get('end')
            if isinstance(end_ts, int):
                now_seconds = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
                remaining_secs = max(0, end_ts - now_seconds)
            else:
                remaining_secs = 0

        hours_remaining = remaining_secs // 3600
        minutes_remaining = (remaining_secs % 3600) // 60

        await ctx.send(
            f"Current ranked map is **{current_map_name}** for **{hours_remaining} hours {minutes_remaining} minutes**. Next map is **{next_map_name}**."
        )

    @commands.command()
    async def split(self, ctx: commands.Context):
        api_key = getattr(config, 'APEX_API_KEY', None)
        if not api_key:
            await ctx.send("APEX_API_KEY is not configured.")
            return

        try:
            async with self.bot.http_client.get(API_URL, headers={"Authorization": api_key}) as resp:
                if resp.status != 200:
                    await ctx.send(f"Failed to fetch ranked rotation (status {resp.status}).")
                    return
                data = await resp.json()
        except Exception as e:
            log.exception("Error fetching Apex ranked rotation: %s", e)
            await ctx.send("Error fetching ranked rotation.")
            return

        current = (data or {}).get('ranked', {}).get('current', {})
        end_ts = current.get('end')
        if not isinstance(end_ts, int):
            await ctx.send("Could not determine ranked split end.")
            return

        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        remaining_secs = max(0, end_ts - now)
        days = remaining_secs // 86400
        hours = (remaining_secs % 86400) // 3600
        await ctx.send(f"Current ranked split ends in: **{days} days {hours} hours**")

    # https://tracker.gg/developers/docs/getting-started
    # @commands.command()
    # async def stats(self, ctx: commands.Context, *, username: str):
    #     """Get Apex Legends stats for a player"""
    #     trn_api_key = config.TRN_API_KEY
    #     async with self.bot.http_client.get(f"https://public-api.tracker.gg/v2/apex/standard/profile/origin/{username}", headers={"TRN-Api-Key": trn_api_key}) as resp:
    #         if resp.status == 200:
    #             data = await resp.json()
    #             stats = data['data']['segments'][0]['stats']
    #             await ctx.send(f"**{username}**'s stats:")

async def setup(bot: Zhenpai):
    await bot.add_cog(Apex(bot))