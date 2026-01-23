from discord.ext import commands
import discord
import logging
import config
from bot import Zhenpai
from typing import Dict, List, Optional, Tuple
import re
from datetime import datetime, timedelta

log: logging.Logger = logging.getLogger(__name__)

# riot name, tag
TFT_SUMMONERS = [
    ("yukiho", "yuki"),
    ("Sunjoy", "CFA"),
    ("headiesbro", "NA1"),
    ("Prab", "0824"),
    ("charles", "chill"),
    ("TripleAKGF", "NA1"),
    ("flatgirlsrcute", "UB3"),
    ("Juqex", "MaldU"),
    ("trashahhnih", "trash"),
    ("cutefatboy", "frick"),
    ("Coolkids", "NA1"),
    ("ycxna", "NA1")
]

REGION = "na1"
TFT_SET_NUMBER = 16

TIER_VALUES = {
    "CHALLENGER": 10,
    "GRANDMASTER": 9,
    "MASTER": 8,
    "DIAMOND": 7,
    "EMERALD": 6,
    "PLATINUM": 5,
    "GOLD": 4,
    "SILVER": 3,
    "BRONZE": 2,
    "IRON": 1,
    "UNRANKED": 0
}

RANK_VALUES = {
    "I": 4,
    "II": 3,
    "III": 2,
    "IV": 1,
}

class Riot(commands.Cog):
    """Commands for Riot Games TFT stats"""

    def __init__(self, bot: Zhenpai):
        self.bot = bot

    async def fetch_tft_data(self, name: str, tag: str) -> Optional[Dict]:
        """Fetch TFT data from API"""
        base_url = config.TFT_TOOLS_BASE_URL
        set_param = TFT_SET_NUMBER * 10
        api_url = f"{base_url}/player/stats2/{REGION}/{name}/{tag}/{set_param}/50"

        try:
            async with self.bot.http_client.get(api_url) as resp:
                if resp.status != 200:
                    log.error(f"Failed to fetch TFT data for {name}#{tag} from tft.tools (status {resp.status})")
                    return None
                log.info(f"fetching for {name}#{tag}")
                data = await resp.json()
                log.info(f"done fetching for {name}#{tag}")

                # Extract rankedLeague from playerInfo
                # Returns [division, LP] like ["PLATINUM I", 92] or ["MASTER I", 199]
                ranked_league = data.get("playerInfo", {}).get("rankedLeague", [])

                # Extract number of ranked games
                games = data.get("queueSeasonStats", {}).get("1100", {}).get("games", 0)

                # Calculate L2DLP: LP gained/lost from last 2 days of ranked games
                matches = data.get("matches", [])
                ranked_matches = [m for m in matches if m.get("queueId") == 1100]

                # Filter for matches in the last 2 days
                three_days_ago = (datetime.now().timestamp() - (2 * 24 * 60 * 60)) * 1000  # 2 days in milliseconds
                recent_ranked = [m for m in ranked_matches if m.get("dateTime", 0) >= three_days_ago]
                l2dlp = sum(m.get("lpDiff", 0) for m in recent_ranked)

                return {
                    "rankedLeague": ranked_league,
                    "games": games,
                    "l2dlp": l2dlp
                }

        except Exception as e:
            log.exception(f"Error fetching TFT data for {name}#{tag}: {e}")
            return None

    def get_rank_string(self, ranked_league: List) -> str:
        """Get the rank string without formatting"""
        if not ranked_league or len(ranked_league) != 2:
            return "Unranked"

        division, lp = ranked_league
        if not division or division == "UNRANKED":
            return "Unranked"

        # Parse the division to extract tier and rank
        parts = division.split()
        tier = parts[0] if parts else division

        # For Master, Grandmaster, Challenger - don't show division
        if tier.upper() in ["MASTER", "GRANDMASTER", "CHALLENGER"]:
            return f"{tier.capitalize()} ({lp} LP)"
        else:
            # Capitalize tier, keep roman numeral uppercase
            formatted_tier = tier.capitalize()
            roman_numeral = parts[1].upper() if len(parts) > 1 else ""
            formatted_division = f"{formatted_tier} {roman_numeral}" if roman_numeral else formatted_tier
            return f"{formatted_division} ({lp} LP)"

    def format_rank(self, ranked_league: List, riot_name: str, games: int = 0, l2dlp: int = 0, name_width: int = 20, rank_width: int = 25) -> str:
        """Format rank information into a table-like string"""
        # Get rank string
        rank_str = self.get_rank_string(ranked_league)

        # Format with padding for alignment using monospace (no markdown)
        name_part = f"{riot_name}:".ljust(name_width + 2)  # +2 for colon and spacing
        rank_part = rank_str.ljust(rank_width + 2)  # +2 for extra spacing
        games_part = f"{games:>3} games" if games >= 0 else ""

        # Add L2DLP with +/- sign (always show sign, right-align in 4 chars)
        l2dlp_part = f"  {l2dlp:+4} LP"

        return f"{name_part}{rank_part}{games_part}{l2dlp_part}".rstrip()

    def parse_rank_for_sorting(self, ranked_league: List) -> Tuple[int, int, int]:
        """Parse rankedLeague list to extract tier, division, and LP for sorting"""
        # rankedLeague is [division, LP]
        # Examples: ["PLATINUM I", 92], ["MASTER I", 199], ["CHALLENGER I", 500]
        if not ranked_league or len(ranked_league) != 2:
            return (0, 0, 0)

        division, lp = ranked_league

        if not division or division == "UNRANKED":
            return (0, 0, 0)

        # Parse division string to extract tier and rank
        # Examples: "PLATINUM I" -> ("PLATINUM", "I"), "MASTER I" -> ("MASTER", "I")
        parts = division.upper().split()
        tier = parts[0] if parts else "UNRANKED"
        rank = parts[1] if len(parts) > 1 else ""

        tier_value = TIER_VALUES.get(tier, 0)
        rank_value = RANK_VALUES.get(rank, 0)

        return (tier_value, rank_value, lp)

    @commands.command()
    async def tft(self, ctx: commands.Context):
        """Get TFT ranks for all friend"""
        message = await ctx.send("Fetching tft stats...")
        player_data = []

        for riot_name, tag in TFT_SUMMONERS:
            data = await self.fetch_tft_data(riot_name, tag)
            if not data:
                log.warning(f"Failed to fetch data for {riot_name}#{tag}")
                continue

            player_data.append({
                "name": riot_name,
                "rankedLeague": data["rankedLeague"],
                "games": data["games"],
                "l2dlp": data["l2dlp"]
            })

        # Sort by rank (highest to lowest)
        player_data.sort(
            key=lambda x: self.parse_rank_for_sorting(x["rankedLeague"]),
            reverse=True
        )

        # Calculate max widths for alignment
        max_name_width = max(len(player["name"]) for player in player_data) if player_data else 10
        max_rank_width = max(len(self.get_rank_string(player["rankedLeague"])) for player in player_data) if player_data else 20

        results = []
        for player in player_data:
            rank_str = self.format_rank(
                player["rankedLeague"],
                player["name"],
                player["games"],
                player["l2dlp"],
                max_name_width,
                max_rank_width
            )
            results.append(rank_str)

        # Wrap in code block for monospace alignment
        description = "```\n" + "\n".join(results) + "\n```" if results else "No players found"

        embed = discord.Embed(
            description=description,
            color=discord.Color.blue()
        )
        embed.set_footer(text="LP change is from last 48 hours")

        await message.edit(content=None, embed=embed)