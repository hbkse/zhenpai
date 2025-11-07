import asyncio
from aiohttp import web
from datetime import datetime
from config import LIVE_MATCH_CHANNEL_ID, GUELO_TEAMS_JSON_URL, FLASK_APP_HOST, FLASK_APP_PROTOCOL
import logging
import discord
from discord.ext import commands, tasks
from typing import List, Dict, Any, Optional, Tuple
from bot import Zhenpai
from .db import CS2MySQLDb, CS2PostgresDb
from .views import LiveMatchView

log: logging.Logger = logging.getLogger(__name__)

class CS2(commands.Cog):
    """ Counter-Strike 2 inhouse tracking for the friends """

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.mysql_db = CS2MySQLDb()
        self.postgres_db = CS2PostgresDb(bot.db_pool)
        self.last_processed_match_id = 0
        self.internal_port = 8081
        self.live_tracking_tasks = {}  # Store active tracking tasks
        self.live_messages = {}  # Store message references

    async def cog_load(self):
        """Initialize database connections and start polling task."""
        try:
            await self.mysql_db.connect()
            log.info(f"CS2 cog loaded and mysql connected.")
            
            # Start the polling task
            self.poll_matches.start()
        except Exception as e:
            log.error(f"Failed to initialize CS2 cog: {e}")

    async def cog_unload(self):
        """Clean up database connections and stop polling task."""
        self.poll_matches.cancel()
        
        # Cancel all live tracking tasks
        for task_id, task in self.live_tracking_tasks.items():
            task.cancel()
        self.live_tracking_tasks.clear()
        self.live_messages.clear()
        
        await self.mysql_db.close()
        log.info("CS2 cog unloaded")

    async def start_internal_server(self):
        """Start internal HTTP server for communication with flask server"""
        app = web.Application()
        app.router.add_post('/start-live-tracking', self.start_live_tracking)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        # Internal server on different port
        site = web.TCPSite(runner, '127.0.0.1', self.internal_port)
        await site.start()
        
        log.info(f"Internal server started on http://127.0.0.1:{self.internal_port}")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.start_internal_server()

# region live tracking
    async def start_live_tracking(self, request):
        """
        Entry point that gets hit when guelo locks in a new match start.
        - Posts an embed to match channel.
        - Polls for the next new matchzy match from mysql
        - Polls and edits embed with live match score
        """
        try:
            # Parse image URL from request
            request_data = {}
            if request.content_type == 'application/json':
                request_data = await request.json()
            image_url = request_data.get('image_url')
            
            channel = self.bot.get_channel(LIVE_MATCH_CHANNEL_ID)
            if channel:
                if not image_url:
                    log.warning("didn't get image_url")

                # Initialize variables
                team1_steamids = []
                team2_steamids = []
                team_win_odds = None
                team_names = None

                async with self.bot.http_client.get(GUELO_TEAMS_JSON_URL) as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        # Extract team names and steamids from team data
                        try:
                            if 'team1' in data and 'players' in data['team1'] and 'name' in data['team1']:
                                team1_name = data['team1']['name']
                                team1_players = data['team1']['players']
                                if isinstance(team1_players, dict):
                                    team1_steamids = [int(steamid64) for steamid64 in team1_players.keys() if steamid64.isdigit()]
                            else:
                                log.warning("No team1 players found in data")

                            if 'team2' in data and 'players' in data['team2'] and 'name' in data['team2']:
                                team2_name = data['team2']['name']
                                team2_players = data['team2']['players']
                                if isinstance(team2_players, dict):
                                    team2_steamids = [int(steamid64) for steamid64 in team2_players.keys() if steamid64.isdigit()]
                            else:
                                log.warning("No team2 players found in data")
                            team_names = (team1_name, team2_name)

                            # Calculate odds if we have enough players
                            if len(team1_steamids) == 5 and len(team2_steamids) == 5:
                                odds_data = await self.postgres_db.calculate_team_odds(team1_steamids, team2_steamids)
                                team_win_odds = (odds_data['team1_odds'] / 100.0, odds_data['team2_odds'] / 100.0)
                            else:
                                log.warning("Not enough players to calculate odds, defaulting to 50/50")
                                team_win_odds = (0.5, 0.5)
                        except Exception as e:
                            log.warning(f"Could not calculate odds: {e}")
                    else:
                        log.warning(f"Failed to fetch from {GUELO_TEAMS_JSON_URL} guelo teams json: {resp.status}")
                        log.warning("can't do shit without team data")

                # Convert steamids to discord_ids for team rosters
                team1_discord_ids = []
                team2_discord_ids = []
                if team1_steamids:
                    team1_discord_ids = await self.postgres_db.get_discord_ids_from_steamids(team1_steamids)
                if team2_steamids:
                    team2_discord_ids = await self.postgres_db.get_discord_ids_from_steamids(team2_steamids)
                team_rosters = (team1_discord_ids, team2_discord_ids)

                # get the next match id that will be created
                last_match_id = await self.mysql_db.get_latest_match_id()
                next_match_id = last_match_id + 1

                live_view = LiveMatchView(
                    match_id=next_match_id,
                    image_url=image_url,
                    team_names=team_names,
                    team_win_odds=team_win_odds,
                    team_rosters=team_rosters
                )

                message = await channel.send(view=live_view)

                # Cancel any existing tasks, just assume there's only ever 1 live match for now
                for task_id, task in self.live_tracking_tasks.items():
                    task.cancel()
                self.live_tracking_tasks.clear()
                self.live_messages.clear()

                # Start live tracking task
                tracking_id = f"live_{datetime.now().timestamp()}"
                self.live_messages[tracking_id] = message

                task = asyncio.create_task(self.poll_live_match(tracking_id, live_view))
                self.live_tracking_tasks[tracking_id] = task
                log.info(f"Started live tracking task: {tracking_id}")

            return web.Response(text='')
        except Exception as e:
            print(f"Discord action error: {e}")
            return web.Response(text='Error', status=500)
        
    async def poll_live_match(self, tracking_id: str, live_view: 'LiveMatchView'):
        """Poll for new matches and start score tracking when found."""
        try:
            log.info(f"Starting live match polling for {tracking_id}")

            # Poll for next match to be created (.start)
            while tracking_id in self.live_messages:
                await asyncio.sleep(2)

                latest_match_id = await self.mysql_db.get_latest_match_id()
                if latest_match_id == live_view.match_id:
                    log.info(f"New match has started: {latest_match_id}")
                    live_view.container.accent_color = discord.Color.green()
                    await self.poll_match_scores(tracking_id, latest_match_id, live_view)
                    break
                elif latest_match_id > live_view.match_id:
                    log.info(f"Match ID jumped ahead from {live_view.match_id} to {latest_match_id}, updating")
                    log.info("Bets placed during this time might be broken LOL")
                    live_view.match_id = latest_match_id
                    await self.poll_match_scores(tracking_id, latest_match_id, live_view)

        except Exception as e:
            log.error(f"Error in live match polling {tracking_id}: {e}")
        finally:
            if tracking_id in self.live_tracking_tasks:
                del self.live_tracking_tasks[tracking_id]
            if tracking_id in self.live_messages:
                del self.live_messages[tracking_id]
    
    async def poll_match_scores(self, tracking_id: str, initial_match_id: int, live_view: 'LiveMatchView'):
        """Poll match scores and update the LiveMatchView. Handles premature match endings by switching to newer matches."""
        try:
            log.info(f"Starting score polling for match {initial_match_id}")
            message : discord.Message = self.live_messages.get(tracking_id)
            if not message:
                log.error(f"No message found for tracking ID {tracking_id}")
                return

            current_match_id = initial_match_id
            last_team1_score = -1
            last_team2_score = -1
            betting_locked = False

            while tracking_id in self.live_messages:
                await asyncio.sleep(5)
                log.info(f"polling for match score updates for {current_match_id}")

                # Check if there's a newer match that started, this happens when people fk up and forceend and restart
                latest_match_id = await self.mysql_db.get_latest_match_id()
                if latest_match_id > current_match_id:
                    log.info(f"Newer match detected: {latest_match_id}, switching from {current_match_id}")
                    current_match_id = latest_match_id
                    live_view.match_id = latest_match_id # this is a nightmare for bets that were created during this time

                    last_team1_score = 0  # Reset score tracking for new match
                    last_team2_score = 0

                # the score data is in map_data, but need match_data for better detection of if the match is complete
                match_data = await self.mysql_db.get_match_by_id(current_match_id)
                map_data = await self.mysql_db.get_map_stats_for_match(current_match_id)
                if not match_data:
                    log.warning(f"No match data found for match ID {current_match_id}")
                    log.warning(f"map data: {map_data}")
                    continue

                team1_score = map_data.get('team1_score', 0) if map_data else 0
                team2_score = map_data.get('team2_score', 0) if map_data else 0

                # Lock betting once pistol round is over
                if not betting_locked and (team1_score > 0 or team2_score > 0):
                    live_view.lock_betting()
                    live_view.stop() # there shouldn't be anymore input
                    betting_locked = True
                    log.info(f"Locked betting for match {current_match_id}")

                # Check if match is complete
                if map_data and self._check_if_complete_match(map_data, match_data):
                    log.info(f"Match {current_match_id} completed")
                    winner = match_data.get('team1_name') if team1_score > team2_score else match_data.get('team2_name')
                    score_text = f"{winner} won! {team1_score} - {team2_score}"
                    live_view.update_score_text(score_text)

                    # Update bets_text with payout/loss information
                    try:
                        all_bets = await self.postgres_db.get_all_match_bets(current_match_id)
                        if all_bets:
                            results_text = "**Match Results:**\n"
                            for bet in all_bets:
                                username = bet.get('discord_username') or f"User {bet['user_id']}"
                                bet_won = bet['team_name'] == winner
                                if bet_won:
                                    profit = bet['payout'] - bet['amount']
                                    results_text += f"{username}: Won **{profit}** points (bet {bet['amount']} on {bet['team_name']})\n"
                                else:
                                    results_text += f"{username}: Lost **{bet['amount']}** points (bet on {bet['team_name']})\n"
                            live_view.bets_text.content = results_text
                        else:
                            live_view.bets_text.content = "No bets were placed on this match."
                    except Exception as e:
                        log.error(f"Error updating bet results: {e}")

                    # delete old message and send new one to push to front of channel
                    try:
                        channel = message.channel
                        await channel.send(view=live_view)
                        await message.delete()
                        log.info(f"Deleted old live tracking message for match {current_match_id}")
                    except Exception as e:
                        log.warning(f"Could not delete old live message: {e}")
                    break

                # Only update if scores changed
                if team1_score != last_team1_score or team2_score != last_team2_score:
                    score_text = f"Live Match Score: {team1_score} - {team2_score}"
                    live_view.update_score_text(score_text)
                    await message.edit(view=live_view)
                    log.info(f"Updated scores for match {current_match_id}: {team1_score}-{team2_score}")

                    last_team1_score = team1_score
                    last_team2_score = team2_score

        except Exception as e:
            log.error(f"Error in score polling for match {current_match_id}: {e}")
        finally:
            # Cleanup
            if tracking_id in self.live_tracking_tasks:
                del self.live_tracking_tasks[tracking_id]
            if tracking_id in self.live_messages:
                del self.live_messages[tracking_id]
# endregion

# region poll_matches
    def _check_if_complete_match(self, maps_data: Dict[str, Any], match_data: Dict[str, Any]):
        """
        Sometimes matchzy doesn't mark an end_time or winner for the match so we should base it off scores.
        """
        # if team1_score or team2_score was set, then match was complete
        match_score_set = (int(match_data['team1_score']) != 0) or (int(match_data['team2_score']) != 0)
        
        # if map_data team score hit 13, 16, 19 etc. , then match was complete, unless ongoing OT
        team1 = int(maps_data['team1_score'])
        team2 = int(maps_data['team2_score'])
        higher = max(team1, team2)
        terminal_round_count_met = higher in [13, 16, 19, 22, 25]
        # check if we're in an ongoing OT scenario, like 13-12 or 16-15 is not terminal
        not_ongoing_overtime = terminal_round_count_met and (abs(team1 - team2) > 1)

        return match_score_set or not_ongoing_overtime

    def _build_match_data(self, maps_data: Dict[str, Any], match_data: Dict[str, Any]):
        winner = match_data['team1_name'] if maps_data['team1_score'] > maps_data['team2_score'] else match_data['team2_name']

        return {
            "matchid": maps_data['matchid'],
            "start_time": maps_data['start_time'],
            "end_time": maps_data['end_time'] or match_data['end_time'] or datetime.utcnow(), # this often doesnt write
            "winner": maps_data['winner'] or match_data['winner'] or winner,
            "mapname": maps_data['mapname'],
            "team1_score": maps_data['team1_score'],
            "team2_score": maps_data['team2_score'],
            "team1_name": match_data['team1_name'],
            "team2_name": match_data['team2_name'],
        }

    # @tasks.loop(seconds=15)
    @tasks.loop(minutes=10)
    async def poll_matches(self):
        """Poll the MatchZy MySQL for new matches and replicate to PostgreSQL."""
        try:
            last_processed_id = await self.postgres_db.get_last_processed_match_id()
            log.info(f"Last processed CS2 matchid: {last_processed_id}")

            # Get new matches from MySQL
            new_matches = await self.mysql_db.get_matches_greater_than_matchid(last_processed_id)
            if not new_matches:
                return
            
            match_ids = [match['matchid'] for match in new_matches]
            log.info(f"Found new matches to replicate to postgres {','.join(map(str, match_ids))}")

            maps_data = []
            for matchid in match_ids:
                map_data = await self.mysql_db.get_map_stats_for_match(matchid)
                maps_data.append(map_data)

            # figure out which matches are real completed matches, and then 
            complete_matches = []
            for map_data, match_data in zip(maps_data, new_matches):
                if not map_data:
                    continue # it's possible there's no map data but there is match data
                if self._check_if_complete_match(map_data, match_data):
                    complete_matches.append(self._build_match_data(map_data, match_data))

            if not complete_matches:
                return

            log.info(f"Found {len(complete_matches)} completed matches to process: {complete_matches}")

            processed_count = 0
            for match_data in complete_matches:
                try:
                    # Gather match and player data from external mysql, then insert all as transaction into postgres
                    matchid = match_data['matchid']
                    log.info(f"Processing matchid {matchid} for cs2 stats.")
                    players_data = await self.mysql_db.get_player_stats_for_match(matchid)
                    match_players = [p for p in players_data if p['team'] != "Spectator"]
                    if len(match_players) != 10:
                        log.warning(f"Not 10 players for {matchid}")

                    await self.postgres_db.process_matchzy_data_transaction(match_data, match_players)

                    # Process bets for this completed match, but should this be part of the loop in points.py?
                    await self.postgres_db.process_cs2_match_bets(matchid, match_data['winner'])

                    processed_count += 1
                    
                except Exception as e:
                    log.error(f"Error processing match {matchid}: {e}")
                    break 
            
            if processed_count > 0:
                log.info(f"Successfully processed {processed_count} matches")
                
        except Exception as e:
            log.error(f"Error in poll_matches task: {e}")

    @poll_matches.before_loop
    async def before_poll_matches(self):
        await self.bot.wait_until_ready()
        log.info(f"Starting {__name__} update loop")

    @poll_matches.after_loop
    async def after_poll_matches(self):
        log.info(f"Stopping {__name__} update loop")
# endregion

    @commands.command()
    async def cs2demo(self, ctx: commands.Context, match_id: int = None):
        """Get download link for CS2 demo files by match ID

        Usage: !cs2demo <matchid>
        Example: !cs2demo 12345
        """
        if match_id is None:
            await ctx.send("❌ Please provide a match ID. Usage: `!cs2demo <matchid>`")
            return

        if match_id <= 0:
            await ctx.send("❌ Match ID must be a positive integer.")
            return

        # Build the download URL
        download_url = f"{FLASK_APP_PROTOCOL}://{FLASK_APP_HOST}/download-demo?matchid={match_id}"

        embed = discord.Embed(
            title="📁 CS2 Demo Download",
            description=f"Click the link below to download demo files for match `{match_id}`",
            color=0x00ff00
        )

        embed.add_field(
            name="🔗 Download Link",
            value=f"[Download Demo(s)]({download_url})",
            inline=False
        )

        embed.add_field(
            name="ℹ️ Note",
            value="If multiple maps were played, all demos will be bundled in a ZIP file.",
            inline=False
        )

        embed.set_footer(text=f"Match ID: {match_id}")

        await ctx.send(embed=embed)

    @commands.command()
    async def testodds(self, ctx: commands.Context):
        """Test command for odds calculation - DELETE AFTER TESTING"""
        try:
            async with self.bot.http_client.get(GUELO_TEAMS_JSON_URL) as resp:
                if resp.status != 200:
                    await ctx.send(f"❌ Failed to fetch team data: {resp.status}")
                    return

                data = await resp.json()

                # Extract steamids from team data
                team1_steamids = []
                team2_steamids = []

                if 'team1' in data and 'players' in data['team1']:
                    team1_players = data['team1']['players']
                    if isinstance(team1_players, dict):
                        team1_steamids = [int(steamid64) for steamid64 in team1_players.keys() if steamid64.isdigit()]

                if 'team2' in data and 'players' in data['team2']:
                    team2_players = data['team2']['players']
                    if isinstance(team2_players, dict):
                        team2_steamids = [int(steamid64) for steamid64 in team2_players.keys() if steamid64.isdigit()]

                if len(team1_steamids) == 0 or len(team2_steamids) == 0:
                    await ctx.send("❌ Could not extract team steamids from data")
                    return

                # Calculate odds
                odds_data = await self.postgres_db.calculate_team_odds(team1_steamids, team2_steamids)
                team1_name = data.get('team1', {}).get('name', 'Team 1')
                team2_name = data.get('team2', {}).get('name', 'Team 2')

                # Create test embed
                embed = discord.Embed(
                    title="🎯 Odds Test Results",
                    color=discord.Color.blue()
                )

                embed.add_field(
                    name="Team Data",
                    value=f"**{team1_name}:** {len(team1_steamids)} players\n**{team2_name}:** {len(team2_steamids)} players",
                    inline=False
                )

                embed.add_field(
                    name="Raw ADR Totals",
                    value=f"**{team1_name}:** {odds_data['team1_adr']:.1f}\n**{team2_name}:** {odds_data['team2_adr']:.1f}",
                    inline=True
                )

                embed.add_field(
                    name="Normalized Sums",
                    value=f"**{team1_name}:** {odds_data['team1_normalized_sum']:.1f}\n**{team2_name}:** {odds_data['team2_normalized_sum']:.1f}",
                    inline=True
                )

                embed.add_field(
                    name="Win Odds",
                    value=f"**{team1_name}:** {odds_data['team1_odds']:.2f}%\n**{team2_name}:** {odds_data['team2_odds']:.2f}%",
                    inline=True
                )

                embed.add_field(
                    name="Debug Info",
                    value=f"Average ADR: {odds_data['average_adr']:.1f}\nADR Difference: {odds_data['team1_normalized_sum'] - odds_data['team2_normalized_sum']:.1f}",
                    inline=False
                )

                embed.set_footer(text="DELETE THIS COMMAND AFTER TESTING")
                await ctx.send(embed=embed)

        except Exception as e:
            log.error(f"Error in testodds command: {e}")
            await ctx.send(f"❌ Error testing odds: {e}")

    @commands.command()
    async def winrate(self, ctx: commands.Context, timeframe: str = "month"):
        """Display win/loss records for all CS2 players

        Usage: !winrate [timeframe]
        - month (default): Shows stats for current month only
        - alltime: Shows all-time stats
        """
        all_time = timeframe.lower() == "alltime"
        try:
            player_records = await self.postgres_db.get_player_winrates(all_time=all_time)

            if not player_records:
                await ctx.send("No CS2 match data found.")
                return

            # Separate players by match count
            qualified = [p for p in player_records if p['total_matches'] >= 10]
            unqualified = [p for p in player_records if p['total_matches'] < 10]

            embed = discord.Embed(
                title="🏆 CS2 Player Win/Loss Records",
                color=discord.Color.green()
            )

            description = "```\n"
            description += f"{'Player':<20} {'Wins':<6} {'Losses':<6} {'WR%':<6}\n"
            description += "─" * 44 + "\n"

            # Add qualified players (10+ matches)
            for record in qualified:
                display_name = record['display_name']
                discord_id = record['discord_id']

                if discord_id:
                    try:
                        member = ctx.guild.get_member(discord_id)
                        if member:
                            display_name = member.display_name
                    except:
                        pass

                name = display_name[:18]
                wins = record['wins']
                losses = record['losses']
                winrate = record['winrate']

                description += f"{name:<20} {wins:<6} {losses:<6} {winrate:<6.1f}\n"

            # Add separator and unqualified players if any exist
            if unqualified:
                description += "\n" + "─" * 44 + "\n"
                description += "Less than 10 matches played:\n"
                description += "─" * 44 + "\n"

                for record in unqualified:
                    display_name = record['display_name']
                    discord_id = record['discord_id']

                    if discord_id:
                        try:
                            member = ctx.guild.get_member(discord_id)
                            if member:
                                display_name = member.display_name
                        except:
                            pass

                    name = display_name[:18]
                    wins = record['wins']
                    losses = record['losses']
                    winrate = record['winrate']

                    description += f"{name:<20} {wins:<6} {losses:<6} {winrate:<6.1f}\n"

            description += "```"
            embed.description = description

            await ctx.send(embed=embed)

        except Exception as e:
            log.error(f"Error in winrate command: {e}")
            await ctx.send("An error occurred while retrieving win/loss records.")

    @commands.command()
    @commands.is_owner()
    async def cs2playerstats(self, ctx: commands.Context, view: str = "standard", timeframe: str = "month"):
        """Display CS2 player statistics summary table

        Usage: !cs2playerstats [view] [timeframe]
        - view: standard (default) or detailed
        - timeframe: month (default) or alltime

        Examples:
        - !cs2playerstats
        - !cs2playerstats detailed
        - !cs2playerstats standard alltime
        - !cs2playerstats detailed alltime
        """
        all_time = timeframe.lower() == "alltime"
        try:
            player_stats = await self.postgres_db.get_comprehensive_player_stats(all_time=all_time)

            if not player_stats:
                await ctx.send("No CS2 match data found.")
                return

            if view.lower() == "detailed":
                await self._send_detailed_stats_table(ctx, player_stats, all_time)
            else:
                await self._send_summary_stats_table(ctx, player_stats, all_time)

        except Exception as e:
            log.error(f"Error in cs2playerstats command: {e}")
            await ctx.send("An error occurred while retrieving player statistics.")

    async def _send_summary_stats_table(self, ctx: commands.Context, player_stats: List[Dict[str, Any]]):
        """Send a summary table of all players' key stats."""
        embed = discord.Embed(
            title="📊 CS2 Player Statistics Summary",
            color=discord.Color.blue()
        )

        description = "```\n"
        description += f"{'Player':<16} {'ADR':<5} {'K/D':<5} {'WR%':<5} {'Matches':<7}\n"
        description += "─" * 50 + "\n"

        for stats in player_stats[:30]:  # Limit to top 30 players
            display_name = stats['display_name']
            discord_id = stats['discord_id']

            if discord_id:
                try:
                    member = ctx.guild.get_member(discord_id)
                    if member:
                        display_name = member.display_name
                except:
                    pass

            name = display_name[:14]
            adr = stats['avg_damage_per_round']
            kd_ratio = stats['kd_ratio']
            winrate = stats['winrate']
            matches = stats['matches_played']

            description += f"{name:<16} {adr:<5.0f} {kd_ratio:<5.2f} {winrate:<5.1f} {matches:<7}\n"

        description += "```"
        embed.description = description
        embed.set_footer(text="Showing top 30 players by ADR • Use 'detailed' for advanced stats")

        await ctx.send(embed=embed)

    async def _send_detailed_stats_table(self, ctx: commands.Context, player_stats: List[Dict[str, Any]]):
        """Send a detailed table of advanced player stats."""
        embed = discord.Embed(
            title="📊 CS2 Advanced Player Statistics",
            color=discord.Color.blue()
        )

        description = "```\n"
        description += f"{'Player':<14} {'HS%':<4} {'V1%':<4} {'Ent%':<4} {'Fl%':<4} {'UD':<4} {'Matches':<7}\n"
        description += "─" * 55 + "\n"

        for stats in player_stats[:30]:  # Limit to top 30 players
            display_name = stats['display_name']
            discord_id = stats['discord_id']

            if discord_id:
                try:
                    member = ctx.guild.get_member(discord_id)
                    if member:
                        display_name = member.display_name
                except:
                    pass

            name = display_name[:12]
            hs_pct = stats['headshot_percentage']
            clutch_pct = stats['clutch_success_rate']
            entry_pct = stats['entry_success_rate']
            flash_pct = stats['flash_success_rate']
            util_dmg = stats['avg_utility_damage']
            matches = stats['matches_played']

            description += f"{name:<14} {hs_pct:<4.0f} {clutch_pct:<4.0f} {entry_pct:<4.0f} {flash_pct:<4.0f} {util_dmg:<4.0f} {matches:<7}\n"

        description += "```"
        embed.description = description
        embed.set_footer(text="HS%=Headshot%, V1%=1v1 Clutch%, Ent%=Entry%, Fl%=Flash%, UD=Utility Damage")

        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def refundbets(self, ctx: commands.Context, match_id: int):
        """Refund all active bets for a specific match.

        Usage: !refundbets <match_id>

        This will:
        - Mark all active bets as inactive
        - Refund the original bet amount to each user
        - All operations happen in a single transaction

        Example: !refundbets 123
        """
        try:
            refunded_count = await self.postgres_db.refund_match_bets(match_id)

            if refunded_count == 0:
                await ctx.send(f"No active bets found for match {match_id}.")
            else:
                await ctx.send(f"Successfully refunded {refunded_count} bet(s) for match {match_id}.")

        except Exception as e:
            log.error(f"Error refunding bets for match {match_id}: {e}")
            await ctx.send(f"Failed to refund bets for match {match_id}: {e}")