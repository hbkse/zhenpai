import discord
import datetime
from typing import List, Dict


class ApexEmbedBuilder:

    @staticmethod
    def create_playing_embed(
        players_in_game: List[Dict],
        players_online: List[Dict]
    ) -> discord.Embed:
        active_players = len(players_in_game) + len(players_online)

        if active_players == 0:
            embed = discord.Embed(
                title="Lobbies?", description="nobody's on", color=0x777777
            )
        else:
            embed = discord.Embed(
                title="Lobbies?",
                color=0x00A3FF if players_in_game else 0x43B581,
            )

            if players_in_game:
                in_game_text = ""
                for player in players_in_game:
                    in_game_text += (
                        f"**{player['playerName']}** - {player['legend']} • "
                        f"{player['rankLabel']} ({player['rankScore']} RP)\n"
                    )

                embed.add_field(
                    name=f"In Game ({len(players_in_game)})",
                    value=in_game_text,
                    inline=False,
                )

            # Add players online but not in game (like in lobby)
            if players_online:
                online_text = ""
                for player in players_online:
                    online_text += (
                        f"**{player['playerName']}** - "
                        f"{player['legend']} • {player['rankLabel']}\n"
                    )

                embed.add_field(
                    name=f"In Lobby ({len(players_online)})",
                    value=online_text,
                    inline=False,
                )

        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)

        embed.set_footer(text=f"Active players: {active_players}")

        return embed
