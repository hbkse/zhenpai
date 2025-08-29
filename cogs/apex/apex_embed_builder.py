import discord
import datetime
import asyncio
from typing import List, Dict, Tuple, Callable


class ApexEmbedBuilder:

    # Loading message states
    LOADING_MESSAGES = [
        "checking to see who's playing...",
        "this is taking a while..",
        "dude..",
        "seriously? is this even working?",
    ]

    @staticmethod
    def create_loading_embed() -> discord.Embed:
        embed = discord.Embed(
            title="Lobbies?",
            description=ApexEmbedBuilder.LOADING_MESSAGES[0],
            color=0x00FF00,  # Green color
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_footer(text="!playing")
        return embed

    @staticmethod
    def create_loading_update_task(
        message: discord.Message, loading_embed: discord.Embed
    ) -> asyncio.Task:
        """Create a background task that updates the loading message every 3 seconds"""

        async def update_loading_message():
            message_index = 0
            while True:
                await asyncio.sleep(3)
                message_index = min(
                    message_index + 1, len(ApexEmbedBuilder.LOADING_MESSAGES) - 1
                )
                new_embed = loading_embed.copy()
                new_embed.description = ApexEmbedBuilder.LOADING_MESSAGES[message_index]
                try:
                    await message.edit(embed=new_embed)
                except Exception:
                    # Message was already edited or deleted
                    break

        return asyncio.create_task(update_loading_message())

    @staticmethod
    async def cancel_loading_task(task: asyncio.Task) -> None:
        """Cancel the loading task and wait for it to finish"""
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @staticmethod
    def create_playing_embed(
        players_in_game: List[Dict], players_online: List[Dict]
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
