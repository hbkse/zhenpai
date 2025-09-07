from discord.ext import commands
import discord
import logging
import datetime
import config
from bot import Zhenpai
from .apex_embed_builder import ApexEmbedBuilder
from .players import DEFAULT_PLAYERS, fetch_player_data, parse_player_info

log: logging.Logger = logging.getLogger(__name__)

API_URL = "https://api.mozambiquehe.re/maprotation?version=2"


class Apex(commands.Cog):
    """Commands for Apex Legends"""

    def __init__(self, bot: Zhenpai):
        self.bot = bot

    @commands.command()
    async def map(self, ctx: commands.Context):
        api_key = getattr(config, "APEX_API_KEY", None)
        if not api_key:
            await ctx.send("APEX_API_KEY is not configured.")
            return

        try:
            async with self.bot.http_client.get(
                API_URL, headers={"Authorization": api_key}
            ) as resp:
                if resp.status != 200:
                    await ctx.send(
                        f"Failed to fetch map rotation (status {resp.status})."
                    )
                    return
                data = await resp.json()
        except Exception as e:
            log.exception("Error fetching Apex map rotation: %s", e)
            await ctx.send("Error fetching map rotation.")
            return

        ranked = (data or {}).get("ranked", {})
        current = ranked.get("current", {})
        next_map_info = ranked.get("next", {})

        current_map_name = current.get("map") or "Unknown"
        next_map_name = next_map_info.get("map") or "Unknown"

        remaining_secs = current.get("remainingSecs")
        if remaining_secs is None:
            end_ts = current.get("end")
            if isinstance(end_ts, int):
                now_seconds = int(
                    datetime.datetime.now(datetime.timezone.utc).timestamp()
                )
                remaining_secs = max(0, end_ts - now_seconds)
            else:
                remaining_secs = 0

        hours_remaining = remaining_secs // 3600
        minutes_remaining = (remaining_secs % 3600) // 60

        await ctx.send(
            f"Current ranked map is **{current_map_name}** for "
            f"**{hours_remaining} hours {minutes_remaining} minutes**. "
            f"Next map is **{next_map_name}**."
        )

    @commands.command()
    async def split(self, ctx: commands.Context):
        """Get the countdown to the next Apex Legends season/split"""
        await ctx.send("Couldn't find a programatic way to do this")
        pass

    @commands.command()
    async def playing(self, ctx: commands.Context):
        """Check which players are currently in game"""
        api_key = getattr(config, "APEX_API_KEY", None)
        if not api_key:
            await ctx.send("APEX_API_KEY is not configured.")
            return

        players_in_game = []
        players_online = []
        players_offline = []

        total_players = len(DEFAULT_PLAYERS)
        processed = 0

        # Send initial progress embed
        message = await ctx.send(
            embed=ApexEmbedBuilder.create_progress_embed(processed, total_players)
        )

        try:
            for i, player_uid in enumerate(DEFAULT_PLAYERS):
                try:
                    log.debug(
                        "Fetching data for player UID %s (%d/%d)",
                        player_uid,
                        i + 1,
                        total_players,
                    )

                    player_data = await fetch_player_data(self.bot, api_key, player_uid)
                    if not player_data:
                        log.warning("No data returned for player UID %s", player_uid)
                        players_offline.append(player_uid)
                        continue

                    if isinstance(player_data, dict) and "error" in player_data:
                        log.warning("API error for player UID %s", player_uid)
                        players_offline.append(player_uid)
                        continue

                    player_info = parse_player_info(player_data, player_uid)
                    if player_info["status"] == "in_game":
                        players_in_game.append(player_info)
                    elif player_info["status"] in ["online", "invite"]:
                        players_online.append(player_info)
                    else:
                        players_offline.append(player_info)

                except Exception as e:
                    log.exception("Error processing player UID %s: %s", player_uid, e)
                    players_offline.append(player_uid)
                finally:
                    processed += 1
                    # Update progress based on processed players
                    try:
                        await message.edit(
                            embed=ApexEmbedBuilder.create_progress_embed(
                                processed, total_players
                            )
                        )
                    except Exception:
                        # If message edit fails (deleted or perms), continue silently
                        pass
        except Exception:
            raise

        # Create and edit message with final embed
        try:
            embed = ApexEmbedBuilder.create_playing_embed(
                players_in_game, players_online
            )
            await message.edit(embed=embed)
        except Exception as e:
            log.exception("Error creating/sending embed: %s", e)
