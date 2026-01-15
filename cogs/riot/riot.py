from discord.ext import commands
import discord
import logging
from bot import Zhenpai
from typing import Dict, List, Optional, Tuple
import re
import json
import asyncio

log: logging.Logger = logging.getLogger(__name__)

# puuid, riot name, tag
PUUIDS = [
    ("Iud4KolGqC_7x6tcBspISnWk-_LmhebOT-bPz6101zZXnRXyo8u3AzvKQjRjLjvmlBGuuU-akUm5FA", "yukiho", "yuki"),
    ("3xlFlw3Sj4TRM8EU8d0ilbCkvBA1gaO0tfRyTvSR-_7A-ot_1tBR65cbsG1Uci4KqTQQGIDlBgwoWQ", "Sunjoy", "CFA"),
    ("l7KRrWXZvkk-6A06cnJpzezJSybbwjl2jv6KldYgCaQlq2fqfmca2c9_XID_2wVb64Zt5weWmU3FuA", "headiesbro", "NA1"),
    ("cbmC-rmgcRsq4iKAoaKG285eZ2S3UnKCfIUYEfq48G73O6sdroOJo51Jt4n0Hns2RwRf0SmTTSS8HQ", "Prab", "0824"),
    ("_aZe1zU_wrDoonukOvkS_bHl1lWTa58eCv5TWJAfnZbxHSuM7qx4agPmInyx0wCMVVc4xpv8pOsthA", "charles", "chill"),
    # ("HGRRGSQ7ugI7ru9bLocaYNe-v8c7jE8batZLmp1eDY8DRfoV507ByhblIvnR2FmoYXfVuxZBvpHJPg", "Im a Railgun", "NA1"),
    ("waE79wXA2UQflf3sIVuYFr_w8tPipymaiYss5ZImdll2y75-WqiDBlFSyONtFWenWcNvFfyymdezJw", "TripleAKGF", "NA1"),
    ("GE2BXEZ-n1-2qdSrctnDsxjoXPAQloBGbjaOBcK9m4a1NjEzLLYua0yckPkyzt1pbvTOLoQDnjO9pA", "flatgirlsrcute", "UB3"),
    ("L41LjdyYhxAZUn0WNuEd3P67IZS9kOCJ9VqSn4Z_uZsdvP-L8_KeK9jIUNUCSSkW38EvWPasWVZPEg", "Juqex", "MaldU"),
    ("uJMVv7Twosa15VG5V3-0JASutvkDqP7pOP-pSGXIZZpjejY673Ahabj97nYSqnyx-PVkWKP_2Ckq8A", "trashahhnih", "trash"),
]

TACTICS_TOOLS_REGION = "na"

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
    """Commands for Riot Games APIs"""

    def __init__(self, bot: Zhenpai):
        self.bot = bot

    async def _fetch_player_json_data(self, name: str, region: str = TACTICS_TOOLS_REGION) -> Optional[Dict]:
        """Fetch and extract JSON data from tactics.tools"""
        url = f"https://tactics.tools/player/{region}/{name}"
        
        try:
            async with self.bot.http_client.get(url) as resp:
                if resp.status != 200:
                    log.error(f"Failed to fetch data for {name} (status {resp.status})")
                    return None
                html = await resp.text()
                return self._extract_json_data(html)
        except Exception as e:
            log.exception(f"Error fetching data for {name}: {e}")
            return None

    def _extract_json_data(self, html: str) -> Optional[Dict]:
        """Extract and parse embedded JSON data from HTML"""
        try:
            json_start = html.find('{"props"')
            if json_start == -1:
                return None
            
            json_str = html[json_start:]
            brace_count = 0
            in_string = False
            escape_next = False
            
            for i, char in enumerate(json_str):
                if escape_next:
                    escape_next = False
                elif char == '\\':
                    escape_next = True
                elif char == '"':
                    in_string = not in_string
                elif not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            try:
                                data = json.loads(json_str[:i + 1])
                                matches = data.get("props", {}).get("pageProps", {}).get("initialData", {}).get("matches", [])
                                if matches and isinstance(matches, list):
                                    return data
                            except (json.JSONDecodeError, KeyError, ValueError):
                                pass
                            break
                if i > 200000:
                    break
            
            return None
        except Exception as e:
            log.debug(f"Error extracting JSON data: {e}")
            return None

    def _parse_rank_from_matches(self, matches: List[Dict]) -> Tuple[str, str, int]:
        """Parse rank from matches data"""
        try:
            if not matches:
                return "UNRANKED", "", 0
            
            ranked_matches = [m for m in matches if m.get("queueId") == 1100]
            if not ranked_matches:
                return "UNRANKED", "", 0
            
            recent_match = sorted(ranked_matches, key=lambda x: x.get("dateTime", 0), reverse=True)[0]
            rank_after = recent_match.get("rankAfter")
            
            if rank_after and isinstance(rank_after, list) and len(rank_after) >= 2:
                rank_str = rank_after[0]  # "PLATINUM I"
                lp = rank_after[1]  # 92
                
                tier_match = re.search(r'(CHALLENGER|GRANDMASTER|MASTER|DIAMOND|EMERALD|PLATINUM|GOLD|SILVER|BRONZE|IRON)', rank_str, re.IGNORECASE)
                if tier_match:
                    tier = tier_match.group(1).upper()
                    rank = ""
                    if tier not in ["CHALLENGER", "GRANDMASTER", "MASTER"]:
                        rank_match = re.search(r'\b([IVX]+)\b', rank_str)
                        if rank_match:
                            rank = rank_match.group(1)
                    return tier, rank, lp
            
            return "UNRANKED", "", 0
        except Exception as e:
            log.exception(f"Error parsing rank: {e}")
            return "UNRANKED", "", 0

    def format_rank(self, tier: str, rank: str, lp: int, riot_name: str, match_stats: Optional[Dict] = None) -> str:
        """Format rank information into a readable string"""
        if tier == "UNRANKED" or not tier:
            base = f"**{riot_name}**: Unranked"
        elif tier in ["CHALLENGER", "GRANDMASTER", "MASTER"]:
            base = f"**{riot_name}**: {tier.capitalize()} ({lp} LP)"
        else:
            base = f"**{riot_name}**: {tier.capitalize()} {rank} ({lp} LP)"
        
        # Add match statistics if available
        if match_stats:
            stats_parts = []
            if match_stats.get("total_games", 0) > 0:
                stats_parts.append(f"{match_stats['total_games']} games")
            if match_stats.get("recent_20_avg"):
                stats_parts.append(f"Avg: {match_stats['recent_20_avg']}")
            
            if stats_parts:
                base += f" | {', '.join(stats_parts)}"
        
        return base

    def get_rank_sort_key(self, tier: str, rank: str, lp: int) -> Tuple[int, int, int]:
        """Generate a sort key for ranking (higher is better)"""
        tier_value = TIER_VALUES.get(tier, -1)
        rank_value = RANK_VALUES.get(rank, 0)  # Master+ don't have ranks
        return (tier_value, rank_value, lp)

    def _parse_match_history(self, matches: List[Dict]) -> Optional[Dict]:
        """Parse match history from matches data"""
        if not matches:
            return None
        
        ranked_matches = [m for m in matches if m.get("queueId") == 1100]
        recent_20 = sorted(ranked_matches, key=lambda x: x.get("dateTime", 0), reverse=True)[:20]
        
        placements = [m.get("info", {}).get("placement") for m in recent_20 
                     if m.get("info", {}).get("placement", 0) > 0]
        avg_placement = sum(placements) / len(placements) if placements else 0
        
        return {
            "total_games": len(ranked_matches),
            "recent_20_avg": round(avg_placement, 2) if avg_placement > 0 else None
        }

    @commands.command()
    async def tft(self, ctx: commands.Context):
        """Get TFT ranks for all friends"""
        message = await ctx.send("Fetching...")
        player_data = []

        for _, riot_name, _ in PUUIDS:
            json_data = await self._fetch_player_json_data(riot_name, TACTICS_TOOLS_REGION)
            if not json_data:
                log.warning(f"Failed to fetch data for {riot_name}, skipping")
                await asyncio.sleep(1)
                continue

            matches = json_data.get("props", {}).get("pageProps", {}).get("initialData", {}).get("matches", [])
            
            tier, rank, lp = self._parse_rank_from_matches(matches)

            try:
                match_stats = self._parse_match_history(matches)
            except Exception as e:
                log.warning(f"Failed to parse match history for {riot_name}: {e}")
                match_stats = None
            
            player_data.append({
                "name": riot_name,
                "tier": tier,
                "rank": rank,
                "lp": lp,
                "match_stats": match_stats
            })
            await asyncio.sleep(1)

        player_data.sort(
            key=lambda x: self.get_rank_sort_key(x["tier"], x["rank"], x["lp"]),
            reverse=True
        )

        if not player_data:
            await message.edit(content="Failed to fetch data for any players")
            return

        results = [
            self.format_rank(p["tier"], p["rank"], p["lp"], p["name"], p.get("match_stats"))
            for p in player_data
        ]

        embed = discord.Embed(
            description="\n".join(results) if results else "No players found",
            color=discord.Color.blue()
        )

        await message.edit(content=None, embed=embed)