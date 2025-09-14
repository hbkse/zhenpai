import discord
import datetime
import colorsys
from typing import List, Dict, Optional


class ApexEmbedBuilder:
    PROGRESS_BAR_WIDTH = 20

    # RP required for each rank in ascending order.
    # Last entry (16000) is Master
    RP_THRESHOLDS_ASC: List[int] = [
        0,
        250,
        500,
        750,
        1000,
        1500,
        2000,
        2500,
        3000,
        3500,
        4000,
        4500,
        5250,
        6000,
        6750,
        7500,
        8250,
        9000,
        10000,
        11000,
        12000,
        13000,
        14000,
        15000,
        16000,
    ]
    APEX_PREDATOR_NOTE = "Top 750 only"

    @staticmethod
    def create_progress_embed(processed: int, total: int) -> discord.Embed:
        """Real progress based on processed players, with nicer visuals."""
        total = max(total, 1)
        pct = max(0.0, min(processed / total, 1.0))

        description = ApexEmbedBuilder._create_progress_text(processed, total, pct)
        embed = discord.Embed(
            title="Lobbies?",
            description=description,
            color=ApexEmbedBuilder._progress_color(pct),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_footer(text="!playing")
        return embed

    @staticmethod
    def _create_progress_text(processed: int, total: int, pct: float) -> str:
        """Create a loading bar with progression."""
        filled = int(round(pct * ApexEmbedBuilder.PROGRESS_BAR_WIDTH))
        empty = ApexEmbedBuilder.PROGRESS_BAR_WIDTH - filled

        bar = "▰" * filled + "▱" * empty

        percent_text = f"{int(pct * 100):>3d}%"
        counts_text = f"{processed}/{total}"

        return (
            f"Fetching player data...\n"
            f"```[{bar}]  {percent_text}  ({counts_text})```"
        )

    @staticmethod
    def _progress_color(pct: float) -> int:
        """
        Smooth gradient from red -> yellow -> green as progress increases.
        Uses HSV hue from 0.0 (red) to ~0.33 (green).
        """
        hue = 0.33 * pct  # 0 = red, 0.33 = green
        r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 1.0)
        r_i, g_i, b_i = int(r * 255), int(g * 255), int(b * 255)
        return (r_i << 16) | (g_i << 8) | b_i

    @staticmethod
    def rp_to_next_rank(rank_score: int) -> Optional[int]:
        """
        Return RP needed to reach the next rank threshold.
        If None: player is at/above Master (next is Predator, top-750 only).
        """
        for t in ApexEmbedBuilder.RP_THRESHOLDS_ASC:
            if rank_score < t:
                return t - rank_score
        return None

    @staticmethod
    def format_rank_progress(rank_score: int) -> str:
        """Human-friendly text for progress toward next rank."""
        rp_to_next = ApexEmbedBuilder.rp_to_next_rank(rank_score)
        if rp_to_next is None:
            return ApexEmbedBuilder.APEX_PREDATOR_NOTE
        return f"{rp_to_next} RP to next rank"

    @staticmethod
    def create_playing_embed(
        players_in_game: List[Dict], players_online: List[Dict]
    ) -> discord.Embed:
        active_players = len(players_in_game) + len(players_online)

        if active_players == 0:
            embed = discord.Embed(
                title="Lobbies?",
                description="nobody's on",
                color=0x777777,
            )
        else:
            embed = discord.Embed(
                title="Lobbies?",
                color=0x00A3FF if players_in_game else 0x43B581,
            )

            if players_in_game:
                in_game_lines = []
                for p in players_in_game:
                    score = int(p.get("rankScore", 0))
                    progress = ApexEmbedBuilder.format_rank_progress(score)
                    in_game_lines.append(
                        f"• **{p['playerName']}** — {p['legend']} • "
                        f"{p['rankLabel']} ({progress})"
                    )
                embed.add_field(
                    name=f"In Game ({len(players_in_game)})",
                    value="\n".join(in_game_lines)[:1024] or "—",
                    inline=False,
                )

            if players_online:
                online_lines = []
                for p in players_online:
                    score = int(p.get("rankScore", 0))
                    progress = ApexEmbedBuilder.format_rank_progress(score)
                    online_lines.append(
                        f"• **{p['playerName']}** — {p['legend']} • "
                        f"{p['rankLabel']} ({progress})"
                    )
                embed.add_field(
                    name=f"🛋️ In Lobby ({len(players_online)})",
                    value="\n".join(online_lines)[:1024] or "—",
                    inline=False,
                )

        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
        embed.set_footer(text=f"Active players: {active_players}")
        return embed
