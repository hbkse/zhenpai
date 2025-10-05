from __future__ import annotations

from discord import ui
import discord
from .db import CS2PostgresDb


class MakeBetModal(ui.Modal):
    bet_explanation = ui.TextDisplay("")
    bet_amount_text_input = ui.TextInput(label='Bet Amount', style=discord.TextStyle.short)

    def __init__(self, view: 'LiveMatchView', team_name: str, user_points: int, team_win_odds: float) -> None:
        self.__view = view
        self.bet_amount_text_input.default = 0

        self.team_name = team_name
        self.user_points = user_points
        self.team_win_odds = team_win_odds

        self.odds = (1 - team_win_odds) / team_win_odds
        self.bet_explanation.content = (
            f"You have **{user_points} points**.\n"
            f"Odds for this team are **1 : {self.odds:.2f}**.\n"
            f"That means for every 1000 points you bet, you can win {self.odds * 1000:.0f} points."
        )
        super().__init__(title=f"Bet on {team_name}")

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        # validate bet amount
        # TODO: there's a bug here where the user can bet multiple times to exceed their points, like leverage
        # should check existing bets and use that to calculate their actual total 
        if self.bet_amount_text_input.value.isdigit() and int(self.bet_amount_text_input.value) > 0:
            bet_amount = int(self.bet_amount_text_input.value)
        else:
            await interaction.response.send_message("Bet amount must be a positive number.", ephemeral=True)
            return
        if bet_amount > self.user_points:
            await interaction.response.send_message(f"You cannot bet more points than you have. You have {self.user_points} points.", ephemeral=True)
            return

        # record the bet in the database
        try:
            db_pool = interaction.client.db_pool
            db = CS2PostgresDb(db_pool)

            await db.insert_match_bet(
                cs_match_id=self.__view.match_id,
                user_id=interaction.user.id,
                amount=bet_amount,
                team_name=self.team_name,
                odds=self.odds
            )
        except Exception as e:
            await interaction.response.send_message(f"Failed to record bet: {e}", ephemeral=True)
            return

        # update the bets_text with the new bet
        if "No bets placed yet." in self.__view.bets_text.content:
            self.__view.bets_text.content = ""
        else:
            self.__view.bets_text.content += "\n"
        self.__view.bets_text.content += f"{interaction.user.display_name} bets {self.bet_amount_text_input.value} points on {self.team_name}."
        await interaction.response.edit_message(view=self.__view)
        self.stop()


class LiveMatchButtons(ui.ActionRow):
    def __init__(self, view: 'LiveMatchView') -> None:
        self.__view = view
        super().__init__()

    @ui.button(label='Bet Team 1', style=discord.ButtonStyle.primary)
    async def button_1(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        user_points = self.__view.user_points_dict.get(interaction.user.id, 0)
        team_name = self.__view.team_names[0]
        team_win_odds = self.__view.team_win_odds[0]
        await interaction.response.send_modal(MakeBetModal(self.__view, team_name=team_name, user_points=user_points, team_win_odds=team_win_odds))

    @ui.button(label='Bet Team 2', style=discord.ButtonStyle.primary)
    async def button_2(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        user_points = self.__view.user_points_dict.get(interaction.user.id, 0)
        team_name = self.__view.team_names[1]
        team_win_odds = self.__view.team_win_odds[1]
        await interaction.response.send_modal(MakeBetModal(self.__view, team_name=team_name, user_points=user_points, team_win_odds=team_win_odds))


class LiveMatchView(ui.LayoutView):
    def __init__(self, *, match_id: int, image_url: str, team_names: tuple[str, str], team_win_odds: tuple, user_points_dict: dict) -> None:
        self.match_id = match_id
        self.team_names = team_names  # (team1_name, team2_name)
        self.team_win_odds = team_win_odds # (team1_win_odds, team2_win_odds)
        self.user_points_dict = user_points_dict
        super().__init__()

        # Image section
        self.match_image = discord.MediaGalleryItem(image_url)
        self.image_header = ui.MediaGallery(self.match_image)

        # Text
        self.score_text = ui.TextDisplay("# Inhouse starting soon!")
        self.odds_text = ui.TextDisplay(f"Win Odds:\n{team_names[0]} - {team_win_odds[0] * 100:.2f}%\n{team_names[1]} - {team_win_odds[1] * 100:.2f}%")
        self.bets_text = ui.TextDisplay("No bets placed yet.")

        # Buttons
        self.buttons = LiveMatchButtons(self)

        container = ui.Container(
            self.score_text,
            self.image_header,
            self.odds_text,
            self.bets_text,
            self.buttons,
            accent_color=discord.Color.yellow()
            )
        self.container = container
        self.add_item(container)

    def update_score_text(self, score_text: str) -> None:
        """Update the match score display."""
        self.score_text.content = f"# {score_text}"

    def lock_betting(self) -> None:
        """Disable betting buttons once pistol is over."""
        self.buttons.button_1.disabled = True
        self.buttons.button_2.disabled = True
