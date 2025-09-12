import asyncio
from datetime import datetime
import discord
from discord.ext import tasks

class TestView(discord.ui.View):
    @discord.ui.button(label='Button 1', style=discord.ButtonStyle.primary)
    async def button1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('Button 1 clicked!')
    
    @discord.ui.button(label='Button 2', style=discord.ButtonStyle.danger)
    async def button2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('Button 2 clicked!')

class ScoreboardComponent(discord.ui.LayoutView):
    def __init__(self, guelo_data, match_state, current_scores=None):
        # parse guelo_data into everything
        self.map = guelo_data['maplist'][0]
        self.team1_name = guelo_data['team1']['name']
        self.team2_name = guelo_data['team2']['name']
        self.team1_players_discord_ids = ['discord']['teamA']
        self.team2_players_discord_ids = ['discord']['teamB']

        self.current_scores = current_scores


    def get_markdown_string(self):
        """"""

class LiveView(discord.ui.View):
    def __init__(self, guelo_data, db_connection):
        super().__init__(timeout=None)  # No timeout since we want persistent polling
        self.db = db_connection
        self.bets = {"team1": [], "team2": []}
        self.message = None
        self.last_db_check = None
        self.is_match_active = True

        teams = list(set(player['team'] for player in guelo_data['participants']))
        self.team1 = teams[0] if len(teams) > 0 else "Team 1"
        self.team2 = teams[1] if len(teams) > 1 else "Team 2"
        
        # Start the polling task
        self.db_poll_task = None
    
    async def start_polling(self):
        """Start the database polling task"""
        if self.db_poll_task is None:
            self.db_poll_task = asyncio.create_task(self.poll_database())
    
    async def stop_polling(self):
        """Stop the database polling task"""
        if self.db_poll_task:
            self.db_poll_task.cancel()
            try:
                await self.db_poll_task
            except asyncio.CancelledError:
                pass
    
    async def poll_database(self):
        """Main polling loop that checks for database changes"""
        while self.is_match_active:
            try:
                await self.check_for_updates()
                await asyncio.sleep(5)  # Poll every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Polling error: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    async def check_for_updates(self):
        """Check database for updates and refresh view if needed"""
        # Check for match status changes
        match_data = await self.get_match_status()
        if match_data and match_data.get('status') == 'finished':
            await self.handle_match_finished(match_data)
            return
        
        # Check for live score updates
        live_data = await self.get_live_data()
        if live_data and self.should_update_view(live_data):
            await self.update_view_with_live_data(live_data)
    
    async def get_match_status(self):
        """Query database for match status"""
        try:
            # Replace with your actual database query
            query = "SELECT status, winner, team1_score, team2_score, updated_at FROM matches WHERE id = ?"
            result = await self.db.fetch_one(query, (self.match_id,))
            return dict(result) if result else None
        except Exception as e:
            print(f"Database query error: {e}")
            return None
    
    async def get_live_data(self):
        """Query database for live match data"""
        try:
            # Replace with your actual database queries
            query = """
            SELECT team1_score, team2_score, current_round, status, updated_at 
            FROM live_matches WHERE match_id = ?
            """
            result = await self.db.fetch_one(query, (self.match_id,))
            return dict(result) if result else None
        except Exception as e:
            print(f"Database query error: {e}")
            return None
    
    def should_update_view(self, live_data):
        """Determine if the view should be updated based on new data"""
        if not live_data:
            return False
        
        # Check if data has changed since last update
        if self.last_db_check is None:
            self.last_db_check = live_data.get('updated_at')
            return True
        
        return live_data.get('updated_at') > self.last_db_check
    
    async def update_view_with_live_data(self, live_data):
        """Update the Discord message with new live data"""
        if not self.message:
            return
        
        try:
            # Create updated embed with live scores
            embed = discord.Embed(
                title="🎮 Live Match - Betting Pool", 
                color=0x00ff00,
                timestamp=datetime.now()
            )
            
            # Add live scores
            embed.add_field(
                name="📊 Live Score",
                value=f"{self.team1}: {live_data.get('team1_score', 0)} - {self.team2}: {live_data.get('team2_score', 0)}",
                inline=False
            )
            
            # Add current round if available
            if live_data.get('current_round'):
                embed.add_field(
                    name="🎯 Current Round",
                    value=f"Round {live_data['current_round']}",
                    inline=True
                )
            
            # Add betting information
            embed.add_field(
                name=f"🔵 {self.team1}", 
                value=f"{len(self.bets['team1'])} bets\n" + 
                      ("\n".join([f"<@{uid}>" for uid in self.bets['team1'][:5]]) if self.bets['team1'] else "No bets yet") +
                      (f"\n... and {len(self.bets['team1'])-5} more" if len(self.bets['team1']) > 5 else ""),
                inline=True
            )
            embed.add_field(
                name=f"🔴 {self.team2}", 
                value=f"{len(self.bets['team2'])} bets\n" + 
                      ("\n".join([f"<@{uid}>" for uid in self.bets['team2'][:5]]) if self.bets['team2'] else "No bets yet") +
                      (f"\n... and {len(self.bets['team2'])-5} more" if len(self.bets['team2']) > 5 else ""),
                inline=True
            )
            
            # Update the message
            await self.message.edit(embed=embed, view=self)
            self.last_db_check = live_data.get('updated_at')
            
        except discord.NotFound:
            # Message was deleted, stop polling
            await self.stop_polling()
        except Exception as e:
            print(f"Error updating view: {e}")
    
    async def handle_match_finished(self, match_data):
        """Handle when match is finished"""
        self.is_match_active = False
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        # Create final embed
        embed = discord.Embed(
            title="🏆 Match Finished!", 
            color=0xff6b6b,
            timestamp=datetime.now()
        )
        
        winner = match_data.get('winner')
        if winner:
            embed.add_field(
                name="🥇 Winner",
                value=f"{winner}",
                inline=False
            )
            
            # Determine winning bettors
            winning_team = "team1" if winner == self.team1 else "team2"
            winners = self.bets[winning_team]
            
            if winners:
                embed.add_field(
                    name="💰 Winning Bettors",
                    value="\n".join([f"<@{uid}>" for uid in winners[:10]]) + 
                          (f"\n... and {len(winners)-10} more" if len(winners) > 10 else ""),
                    inline=False
                )
        
        embed.add_field(
            name="📊 Final Score",
            value=f"{self.team1}: {match_data.get('team1_score', 0)} - {self.team2}: {match_data.get('team2_score', 0)}",
            inline=False
        )
        
        try:
            await self.message.edit(embed=embed, view=self)
        except Exception as e:
            print(f"Error updating final message: {e}")
        
        # Stop polling
        await self.stop_polling()
    
    @discord.ui.button(label="Bet on Team 1", style=discord.ButtonStyle.primary, emoji="🎯")
    async def bet_team1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_bet(interaction, "team1", self.team1)
    
    @discord.ui.button(label="Bet on Team 2", style=discord.ButtonStyle.primary, emoji="🎯")
    async def bet_team2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_bet(interaction, "team2", self.team2)
    
    async def handle_bet(self, interaction: discord.Interaction, team_key: str, team_name: str):
        # Same as before, but also store bet in database
        user = interaction.user
        
        if user.id in self.bets["team1"] or user.id in self.bets["team2"]:
            await interaction.response.send_message("You've already placed a bet!", ephemeral=True)
            return
        
        # Store bet in database
        try:
            await self.db.execute(
                "INSERT INTO bets (match_id, user_id, team, created_at) VALUES (?, ?, ?, ?)",
                (self.match_id, user.id, team_name, datetime.now())
            )
        except Exception as e:
            print(f"Error storing bet: {e}")
            await interaction.response.send_message("Error placing bet, please try again!", ephemeral=True)
            return
        
        self.bets[team_key].append(user.id)
        
        # Force an immediate view update
        live_data = await self.get_live_data()
        if live_data:
            await self.update_view_with_live_data(live_data)
        
        await interaction.response.send_message(f"Bet placed on {team_name}! 🎯", ephemeral=True)