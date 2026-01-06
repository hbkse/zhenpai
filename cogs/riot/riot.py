from discord.ext import commands
import discord
import logging
import config
from bot import Zhenpai
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import re

log: logging.Logger = logging.getLogger(__name__)

# riot name, tag
SUMMONERS = [
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
    ("Coolkids", "NA1")
]

REGION = "na"

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

    async def scrape_tft_opgg(self, name: str, tag: str) -> Optional[Dict]:
        """Scrape TFT data from op.gg"""
        base_url = config.TFT_OP_GG_BASE_URL
        # URL format: /summoners/na/name-tag
        summoner_url = f"{base_url}/summoners/{REGION}/{name}-{tag}"

        try:
            async with self.bot.http_client.get(summoner_url) as resp:
                if resp.status != 200:
                    log.error(f"Failed to fetch TFT data for {name}#{tag} from op.gg (status {resp.status})")
                    return None

                html = await resp.text()
                soup = BeautifulSoup(html, 'lxml')

                # Extract current rank
                rank_text = "UNRANKED"
                rank_element = soup.select_one('.rank')
                if rank_element:
                    rank_text = rank_element.get_text(strip=True)

                # Extract LP
                lp = 0
                lp_element = soup.select_one('.lp')
                if lp_element:
                    lp_match = re.search(r'(\d+)', lp_element.get_text())
                    if lp_match:
                        lp = int(lp_match.group(1))

                # Extract total ranked games played
                ranked_games = 0
                games_element = soup.select_one('.total-games')
                if games_element:
                    games_match = re.search(r'(\d+)', games_element.get_text())
                    if games_match:
                        ranked_games = int(games_match.group(1))

                # Extract last 30 games average placement
                avg_place = 0.0
                avg_place_element = soup.select_one('.avg-placement')
                if avg_place_element:
                    avg_match = re.search(r'(\d+\.?\d*)', avg_place_element.get_text())
                    if avg_match:
                        avg_place = float(avg_match.group(1))

                return {
                    "rank": rank_text,
                    "lp": lp,
                    "ranked_games": ranked_games,
                    "avg_placement": avg_place
                }

        except Exception as e:
            log.exception(f"Error scraping TFT data for {name}#{tag}: {e}")
            return None

    def format_rank(self, rank_text: str, riot_name: str, ranked_games: int = 0, avg_placement: float = 0.0) -> str:
        """Format rank information into a readable string"""
        base = f"**{riot_name}**: {rank_text}"

        # Add ranked games count
        if ranked_games > 0:
            base += f" | {ranked_games} games"

        # Add average placement
        if avg_placement > 0:
            base += f" | Avg: {avg_placement:.2f}"

        return base

    def parse_rank_for_sorting(self, rank_text: str) -> Tuple[int, int, int]:
        """Parse rank text to extract tier, division, and LP for sorting"""
        # Example formats: "DIAMOND II 45 LP", "MASTER 234 LP", "UNRANKED"
        rank_upper = rank_text.upper()

        # Extract LP
        lp = 0
        lp_match = re.search(r'(\d+)\s*LP', rank_upper)
        if lp_match:
            lp = int(lp_match.group(1))

        # Extract tier
        tier_value = 0
        for tier, value in TIER_VALUES.items():
            if tier in rank_upper:
                tier_value = value
                break

        # Extract division (I, II, III, IV)
        rank_value = 0
        for rank, value in RANK_VALUES.items():
            if f' {rank} ' in rank_upper or rank_upper.endswith(f' {rank}'):
                rank_value = value
                break

        return (tier_value, rank_value, lp)

    @commands.command()
    async def tft(self, ctx: commands.Context):
        """Get TFT ranks for all friends from op.gg"""
        message = await ctx.send("Fetching from op.gg...")
        player_data = []

        for riot_name, tag in SUMMONERS:
            data = await self.scrape_tft_opgg(riot_name, tag)
            if not data:
                log.warning(f"Failed to fetch data for {riot_name}#{tag}")
                continue

            player_data.append({
                "name": riot_name,
                "rank": data["rank"],
                "ranked_games": data["ranked_games"],
                "avg_placement": data["avg_placement"]
            })

        # Sort by rank (highest to lowest)
        player_data.sort(
            key=lambda x: self.parse_rank_for_sorting(x["rank"]),
            reverse=True
        )

        results = []
        for player in player_data:
            rank_str = self.format_rank(
                player["rank"],
                player["name"],
                player["ranked_games"],
                player["avg_placement"]
            )
            results.append(rank_str)

        embed = discord.Embed(
            description="\n".join(results) if results else "No players found",
            color=discord.Color.blue()
        )

        await message.edit(content=None, embed=embed)