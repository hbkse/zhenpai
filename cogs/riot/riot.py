from discord.ext import commands
import discord
import logging
import config
from bot import Zhenpai
from typing import Dict, List, Optional, Tuple
import re
import json

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

REGION = "na1"
TACTICS_TOOLS_REGION = "na"  # Map na1 to na for tactics.tools

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

    async def get_puuid_from_name(self, name: str, tag: str) -> str:
        """Get PUUID from name using tactics.tools (if needed)"""
        # This function may not be needed if we're using tactics.tools directly
        # Keeping for backwards compatibility but may not be used
        url = f"https://tactics.tools/player/{TACTICS_TOOLS_REGION}/{name}"
        
        try:
            async with self.bot.http_client.get(url) as resp:
                if resp.status != 200:
                    log.error(f"Failed to fetch data for {name} from tactics.tools: {resp.status}")
                    return None
                # Try to parse as JSON first
                try:
                    data = await resp.json()
                    # Extract PUUID if available in JSON response
                    return data.get("puuid")
                except:
                    # If not JSON, try to extract from HTML
                    html = await resp.text()
                    # Look for PUUID in the HTML (this is a placeholder - adjust based on actual HTML structure)
                    puuid_match = re.search(r'"puuid":\s*"([^"]+)"', html)
                    if puuid_match:
                        return puuid_match.group(1)
                    return None
        except Exception as e:
            log.exception(f"Error fetching data for {name} from tactics.tools: {e}")
            return None

    async def get_tft_rank_by_name(self, name: str, region: str = TACTICS_TOOLS_REGION) -> Optional[Tuple]:
        """Fetch TFT rank data from tactics.tools using player name"""
        url = f"https://tactics.tools/player/{region}/{name}"

        try:
            async with self.bot.http_client.get(url) as resp:
                if resp.status != 200:
                    log.error(f"Failed to fetch TFT rank for {name} from tactics.tools (status {resp.status})")
                    return None
                
                # Check content type first
                content_type = resp.headers.get('Content-Type', '').lower()
                
                # Try to parse as JSON first if content type suggests it
                if 'application/json' in content_type:
                    try:
                        data = await resp.json()
                        # Extract TFT rank data from JSON response
                        # Adjust these keys based on actual tactics.tools JSON structure
                        tft_data = data.get("tft", {}) or data.get("rankedTFT", {}) or data
                        tier = tft_data.get("tier") or tft_data.get("rank")
                        rank = tft_data.get("rank") or tft_data.get("division")
                        leaguePoints = tft_data.get("leaguePoints") or tft_data.get("lp") or 0
                        
                        if not tier:
                            return "UNRANKED", "", 0
                        
                        return tier.upper(), rank, leaguePoints
                    except (json.JSONDecodeError, Exception):
                        # If JSON parsing fails, fall through to HTML parsing
                        pass
                
                # If not JSON, parse HTML
                html = await resp.text()
                return self._parse_tft_rank_from_html(html)
        except Exception as e:
            log.exception(f"Error fetching TFT rank for {name} from tactics.tools: {e}")
            return None

    def _parse_tft_rank_from_html(self, html: str) -> Optional[Tuple]:
        """Parse TFT rank information from HTML response"""
        try:
            # Try to find rank data in various possible formats
            # Look for tier (e.g., "DIAMOND", "MASTER", etc.)
            tier_match = re.search(r'(?i)(CHALLENGER|GRANDMASTER|MASTER|DIAMOND|EMERALD|PLATINUM|GOLD|SILVER|BRONZE|IRON|UNRANKED)', html)
            tier = tier_match.group(1).upper() if tier_match else "UNRANKED"
            
            if tier == "UNRANKED":
                return "UNRANKED", "", 0
            
            # Look for rank division (I, II, III, IV) - not applicable for Master+
            rank = ""
            if tier not in ["CHALLENGER", "GRANDMASTER", "MASTER"]:
                rank_match = re.search(r'\b([IVX]+)\b', html)
                if rank_match:
                    rank = rank_match.group(1)
            
            # Look for LP/league points - try multiple patterns
            lp_match = None
            # Pattern 1: "123 LP" or "123LP"
            lp_match = re.search(r'(\d+)\s*LP\b', html, re.IGNORECASE)
            if not lp_match:
                # Pattern 2: "league points: 123" or similar
                lp_match = re.search(r'(?:league\s*points?|lp)[:\s]+(\d+)', html, re.IGNORECASE)
            if not lp_match:
                # Pattern 3: Look for numbers near tier/rank mentions
                lp_match = re.search(r'(?:MASTER|DIAMOND|EMERALD|PLATINUM|GOLD|SILVER|BRONZE|IRON)[^0-9]*(\d+)\s*(?:LP|points?)', html, re.IGNORECASE)
            if not lp_match:
                # Pattern 4: Look in data attributes or JSON-like structures
                lp_match = re.search(r'["\'](?:lp|leaguePoints)["\']\s*[:=]\s*(\d+)', html, re.IGNORECASE)
            
            leaguePoints = int(lp_match.group(1)) if lp_match else 0
            
            # Alternative: look for JSON data embedded in HTML
            json_match = re.search(r'<script[^>]*>.*?({[^}]*"tier"[^}]*}).*?</script>', html, re.DOTALL | re.IGNORECASE)
            if json_match:
                try:
                    json_data = json.loads(json_match.group(1))
                    tier = json_data.get("tier", tier).upper()
                    rank = json_data.get("rank", rank)
                    leaguePoints = json_data.get("leaguePoints", json_data.get("lp", leaguePoints))
                except:
                    pass
            
            return tier, rank, leaguePoints
        except Exception as e:
            log.exception(f"Error parsing TFT rank from HTML: {e}")
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

    def _extract_match_data_from_html(self, html: str) -> Optional[List[Dict]]:
        """Extract match history data from HTML page"""
        try:
            # Look for the embedded JSON data in script tags
            # The data is typically in a script tag with structure like:
            # {"props":{"pageProps":{"initialData":{"matches":[...]}}}}
            script_pattern = r'<script[^>]*>(.*?)</script>'
            scripts = re.findall(script_pattern, html, re.DOTALL)
            
            for script_content in scripts:
                # Look for scripts that contain match data
                if 'matches' in script_content and 'placement' in script_content:
                    try:
                        # Find the start of the JSON object containing props
                        start_idx = script_content.find('{"props"')
                        if start_idx == -1:
                            continue
                        
                        # Extract from start_idx and try to find the complete JSON object
                        json_str = script_content[start_idx:]
                        
                        # Try to find the end by matching braces
                        brace_count = 0
                        in_string = False
                        escape_next = False
                        end_idx = -1
                        
                        for i, char in enumerate(json_str):
                            if escape_next:
                                escape_next = False
                                continue
                            
                            if char == '\\':
                                escape_next = True
                                continue
                            
                            if char == '"' and not escape_next:
                                in_string = not in_string
                                continue
                            
                            if in_string:
                                continue
                            
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i + 1
                                    break
                        
                        if end_idx > 0:
                            json_str = json_str[:end_idx]
                            data = json.loads(json_str)
                            matches = data.get("props", {}).get("pageProps", {}).get("initialData", {}).get("matches", [])
                            if matches and isinstance(matches, list):
                                return matches
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        log.debug(f"Failed to parse JSON from script: {e}")
                        continue
            
            return None
        except Exception as e:
            log.exception(f"Error extracting match data from HTML: {e}")
            return None

    async def get_match_history(self, name: str, region: str = TACTICS_TOOLS_REGION) -> Optional[Dict]:
        """Fetch match history data from tactics.tools"""
        url = f"https://tactics.tools/player/{region}/{name}"
        
        try:
            async with self.bot.http_client.get(url) as resp:
                if resp.status != 200:
                    log.error(f"Failed to fetch match history for {name} from tactics.tools (status {resp.status})")
                    return None
                
                html = await resp.text()
                matches = self._extract_match_data_from_html(html)
                
                if not matches:
                    return None
                
                # Filter for ranked games (queueId 1100 is ranked)
                ranked_matches = [m for m in matches if m.get("queueId") == 1100]
                
                # Get current season start (approximate - TFT seasons typically start in January)
                # For now, we'll use all matches as "this season"
                # You can refine this based on dateTime if needed
                current_season_matches = ranked_matches
                
                # Get most recent 20 games
                recent_20 = sorted(current_season_matches, key=lambda x: x.get("dateTime", 0), reverse=True)[:20]
                
                # Calculate average placement
                if recent_20:
                    placements = [m.get("info", {}).get("placement", 0) for m in recent_20 if m.get("info", {}).get("placement") and m.get("info", {}).get("placement") > 0]
                    avg_placement = sum(placements) / len(placements) if placements else 0
                else:
                    avg_placement = 0
                
                return {
                    "total_games": len(current_season_matches),
                    "recent_20_avg": round(avg_placement, 2) if avg_placement > 0 else None,
                    "recent_20_count": len(recent_20)
                }
        except Exception as e:
            log.exception(f"Error fetching match history for {name}: {e}")
            return None

    @commands.command()
    async def tft(self, ctx: commands.Context):
        """Get TFT ranks for all friends"""
        message = await ctx.send("Fetching...")
        player_data = []

        for puuid, riot_name, tag in PUUIDS:
            # Fetch rank info
            rank_info = await self.get_tft_rank_by_name(riot_name, TACTICS_TOOLS_REGION)
            if not rank_info:
                log.warning(f"Failed to fetch rank for {riot_name}, skipping")
                continue

            tier, rank, lp = rank_info
            
            # Fetch match history stats (continue even if this fails)
            try:
                match_stats = await self.get_match_history(riot_name, TACTICS_TOOLS_REGION)
            except Exception as e:
                log.warning(f"Failed to fetch match history for {riot_name}: {e}")
                match_stats = None
            
            player_data.append({
                "name": riot_name,
                "tier": tier,
                "rank": rank,
                "lp": lp,
                "match_stats": match_stats
            })

        player_data.sort(
            key=lambda x: self.get_rank_sort_key(x["tier"], x["rank"], x["lp"]),
            reverse=True
        )

        if not player_data:
            await message.edit(content="Failed to fetch data for any players")
            return

        results = []
        for player in player_data:
            rank_str = self.format_rank(
                player["tier"], 
                player["rank"], 
                player["lp"], 
                player["name"],
                player.get("match_stats")
            )
            results.append(rank_str)

        embed = discord.Embed(
            description="\n".join(results) if results else "No players found",
            color=discord.Color.blue()
        )

        await message.edit(content=None, embed=embed)