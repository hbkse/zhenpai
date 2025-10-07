from __future__ import annotations

from discord import ui
import discord
from .db import CS2PostgresDb


class MakeBetModal(ui.Modal):
    bet_explanation = ui.TextDisplay("")
    bet_amount_text_input = ui.TextInput(label='Bet Amount', style=discord.TextStyle.short)

    def __init__(self, view: 'LiveMatchView', team_name: str, team_index: int, user_points: int, team_win_odds: float) -> None:
        self.__view = view
        self.bet_amount_text_input.default = 0

        self.team_name = team_name
        self.team_index = team_index  # 0 for team1, 1 for team2
        self.user_points = user_points
        self.team_win_odds = team_win_odds

        example_payout = int(1000 / team_win_odds)
        example_profit = example_payout - 1000

        self.bet_explanation.content = (
            f"You have **{user_points} points**.\n"
            f"This team has a **{team_win_odds * 100:.1f}% win chance**.\n"
            f"For a 1000 point bet, you get back **{example_payout} points** if you win (profit: **{example_profit}**)."
        )
        super().__init__(title=f"Bet on {team_name}")

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        # validate bet amount
        if self.bet_amount_text_input.value.isdigit() and int(self.bet_amount_text_input.value) > 0:
            bet_amount = int(self.bet_amount_text_input.value)
        else:
            await interaction.response.send_message("Bet amount must be a positive number.", ephemeral=True)
            return
        if bet_amount > self.user_points:
            await interaction.response.send_message(f"You cannot bet more points than you have. You have {self.user_points} points.", ephemeral=True)
            return

        # Check if user is playing in the match
        team1_roster, team2_roster = self.__view.team_rosters
        user_on_team1 = interaction.user.id in team1_roster
        user_on_team2 = interaction.user.id in team2_roster

        # Prevent betting against your own team
        if user_on_team1 and self.team_index == 1:
            await interaction.response.send_message(
                f"You cannot bet against your own team! You are playing on {self.__view.team_names[0]}.",
                ephemeral=True
            )
            return
        if user_on_team2 and self.team_index == 0:
            await interaction.response.send_message(
                f"You cannot bet against your own team! You are playing on {self.__view.team_names[1]}.",
                ephemeral=True
            )
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
                odds=self.team_win_odds
            )
        except Exception as e:
            await interaction.response.send_message(f"Failed to record bet: {e}", ephemeral=True)
            return

        # update the bet totals
        if self.team_index == 0:
            self.__view.team1_total_bet += bet_amount
        else:
            self.__view.team2_total_bet += bet_amount

        # update the bet totals display
        self.__view.bet_totals_text.content = (
            f"Total Bet:\n"
            f"{self.__view.team_names[0]}: {self.__view.team1_total_bet} points\n"
            f"{self.__view.team_names[1]}: {self.__view.team2_total_bet} points"
        )

        # update the bets_text with the new bet
        if "No bets placed yet." in self.__view.bets_text.content:
            self.__view.bets_text.content = ""
        else:
            self.__view.bets_text.content += "\n"
        self.__view.bets_text.content += f"{interaction.user.display_name} bets **{self.bet_amount_text_input.value}** points on {self.team_name}."
        await interaction.response.edit_message(view=self.__view)
        self.stop()


class LiveMatchButtons(ui.ActionRow):
    def __init__(self, view: 'LiveMatchView') -> None:
        self.__view = view
        super().__init__()

    @ui.button(label='Bet Team 1', style=discord.ButtonStyle.primary)
    async def button_1(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # Query user's current balance
        db_pool = interaction.client.db_pool
        db = CS2PostgresDb(db_pool)
        user_points = await db.get_user_balance(interaction.user.id)

        team_name = self.__view.team_names[0]
        team_win_odds = self.__view.team_win_odds[0]
        await interaction.response.send_modal(MakeBetModal(self.__view, team_name=team_name, team_index=0, user_points=user_points, team_win_odds=team_win_odds))

    @ui.button(label='Bet Team 2', style=discord.ButtonStyle.primary)
    async def button_2(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # Query user's current balance
        db_pool = interaction.client.db_pool
        db = CS2PostgresDb(db_pool)
        user_points = await db.get_user_balance(interaction.user.id)

        team_name = self.__view.team_names[1]
        team_win_odds = self.__view.team_win_odds[1]
        await interaction.response.send_modal(MakeBetModal(self.__view, team_name=team_name, team_index=1, user_points=user_points, team_win_odds=team_win_odds))


class LiveMatchView(ui.LayoutView):
    def __init__(self, *, match_id: int, image_url: str, team_names: tuple[str, str], team_win_odds: tuple, team_rosters: tuple[list[int], list[int]]) -> None:
        self.match_id = match_id
        self.team_names = team_names  # (team1_name, team2_name)
        self.team_win_odds = team_win_odds # (team1_win_odds, team2_win_odds)
        self.team_rosters = team_rosters  # (team1_discord_ids, team2_discord_ids)
        self.team1_total_bet = 0  # Track total bet on team 1
        self.team2_total_bet = 0  # Track total bet on team 2
        super().__init__()

        # Image section
        self.match_image = discord.MediaGalleryItem(image_url)
        self.image_header = ui.MediaGallery(self.match_image)

        # Text
        self.score_text = ui.TextDisplay("# Inhouse starting soon!")
        self.odds_text = ui.TextDisplay(f"Win Odds:\n{team_names[0]} - {team_win_odds[0] * 100:.2f}%\n{team_names[1]} - {team_win_odds[1] * 100:.2f}%")
        self.bet_totals_text = ui.TextDisplay(f"Total Bet:\n{team_names[0]}: 0 points\n{team_names[1]}: 0 points")
        self.bets_text = ui.TextDisplay("No bets placed yet.")

        # Buttons
        self.buttons = LiveMatchButtons(self)

        container = ui.Container(
            self.score_text,
            self.image_header,
            self.odds_text,
            self.bet_totals_text,
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
