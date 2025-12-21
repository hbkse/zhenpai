from discord.ext import commands
import discord
import logging
import config
from bot import Zhenpai
from typing import Dict, List, Optional, Tuple

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
        """"""
        account_region = "americas" # not sure difference between this and the "na1" region
        account_url = f"https://{account_region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
        headers = {"X-Riot-Token": config.RIOT_API_KEY}

        try:
            async with self.bot.http_client.get(account_url, headers=headers) as resp:
                if resp.status != 200:
                    log.error(f"Failed to fetch puuid for name {name}#{tag} {resp.status} {resp.json()}")
                    return None
                account_data = await resp.json()
                puuid = account_data["puuid"]
                return puuid
        except Exception as e:
            log.exception(f"Error fetching summoner {name}#{tag}: {e}")
            return None

    async def get_tft_rank_by_puuid(self, puuid: str) -> Optional[Tuple]:
        """Fetch TFT rank data for a puuid"""
        url = f"https://{REGION}.api.riotgames.com/tft/league/v1/by-puuid/{puuid}"
        headers = {"X-Riot-Token": config.RIOT_API_KEY}

        try:
            async with self.bot.http_client.get(url, headers=headers) as resp:
                if resp.status != 200:
                    log.error(f"Failed to fetch TFT rank for puuid {puuid} (status {resp.status})")
                    return None
                rank_data = await resp.json()

                # unranked case is 200 with empty list
                if len(rank_data) != 1:
                    return "UNRANKED", "", 0
                
                rank_data = rank_data[0]
                tier = rank_data.get("tier")
                rank = rank_data.get("rank")
                leaguePoints = rank_data.get("leaguePoints")
                return tier, rank, leaguePoints
        except Exception as e:
            log.exception(f"Error fetching TFT rank for {puuid}: {e}")
            return None

    def format_rank(self, tier: str, rank: str, lp: int, riot_name: str) -> str:
        """Format rank information into a readable string"""
        if tier == "UNRANKED" or not tier:
            return f"**{riot_name}**: Unranked"

        if tier in ["CHALLENGER", "GRANDMASTER", "MASTER"]:
            return f"**{riot_name}**: {tier.capitalize()} ({lp} LP)"
        else:
            return f"**{riot_name}**: {tier.capitalize()} {rank} ({lp} LP)"

    def get_rank_sort_key(self, tier: str, rank: str, lp: int) -> Tuple[int, int, int]:
        """Generate a sort key for ranking (higher is better)"""
        tier_value = TIER_VALUES.get(tier, -1)
        rank_value = RANK_VALUES.get(rank, 0)  # Master+ don't have ranks
        return (tier_value, rank_value, lp)

    @commands.command()
    async def tft(self, ctx: commands.Context):
        """Get TFT ranks for all friends"""
        api_key = getattr(config, "RIOT_API_KEY", None)
        if not api_key:
            await ctx.send("Bot is missing Riot API key! (idiot)")
            return

        message = await ctx.send("Fetching...")
        player_data = []

        for puuid, riot_name, tag in PUUIDS:
            rank_info = await self.get_tft_rank_by_puuid(puuid)
            if not rank_info:
                await message.edit(content=f"Failed to fetch rank for {riot_name}")
                return

            tier, rank, lp = rank_info
            player_data.append({
                "name": riot_name,
                "tier": tier,
                "rank": rank,
                "lp": lp
            })

        player_data.sort(
            key=lambda x: self.get_rank_sort_key(x["tier"], x["rank"], x["lp"]),
            reverse=True
        )

        results = []
        for player in player_data:
            rank_str = self.format_rank(player["tier"], player["rank"], player["lp"], player["name"])
            results.append(rank_str)

        embed = discord.Embed(
            description="\n".join(results) if results else "No players found",
            color=discord.Color.blue()
        )

        await message.edit(content=None, embed=embed)