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
from .live_view import LiveView, TestView

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
                # Create embed with image as the center piece
                embed = discord.Embed(title="Inhouse starting soon!", color=discord.Color.yellow())
                
                if image_url:
                    embed.set_image(url=image_url)
                else:
                    log.warning("didn't get image_url")

                async with self.bot.http_client.get(GUELO_TEAMS_JSON_URL) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        embed.set_footer(text="Work in progress to bet points from this embed!")
                        
                        message = await channel.send(embed=embed)
                    else:
                        log.warning(f"Failed to fetch from {GUELO_TEAMS_JSON_URL} guelo teams json: {resp.status}")
                        message = await channel.send(embed=embed)

                # Cancel any existing tasks, just assume there's only ever 1 live match for now
                for task_id, task in self.live_tracking_tasks.items():
                    task.cancel()
                self.live_tracking_tasks.clear()
                self.live_messages.clear()

                # Start live tracking task
                tracking_id = f"live_{datetime.now().timestamp()}"
                self.live_messages[tracking_id] = message
                
                task = asyncio.create_task(self.poll_live_match(tracking_id, image_url))
                self.live_tracking_tasks[tracking_id] = task
                log.info(f"Started live tracking task: {tracking_id}")

            return web.Response(text='')
        except Exception as e:
            print(f"Discord action error: {e}")
            return web.Response(text='Error', status=500)
        
    async def poll_live_match(self, tracking_id: str, image_url: str):
        """Poll for new matches and start score tracking when found."""
        try:
            log.info(f"Starting live match polling for {tracking_id}")
            last_match_id = await self.mysql_db.get_latest_match_id()
            log.info(f"Current latest match ID {last_match_id}, now waiting for new match to be created")
            
            # Poll for new match creation
            while tracking_id in self.live_messages:
                await asyncio.sleep(2)
                log.info(f"polling for new matchzy match to be created after {last_match_id}")

                latest_match_id = await self.mysql_db.get_latest_match_id()
                if latest_match_id > last_match_id:
                    log.info(f"New match detected: {latest_match_id}")
                    await self.poll_match_scores(tracking_id, latest_match_id, image_url)
                    break
                    
        except Exception as e:
            log.error(f"Error in live match polling {tracking_id}: {e}")
        finally:
            if tracking_id in self.live_tracking_tasks:
                del self.live_tracking_tasks[tracking_id]
            if tracking_id in self.live_messages:
                del self.live_messages[tracking_id]
    
    async def poll_match_scores(self, tracking_id: str, initial_match_id: int, image_url: str):
        """Poll match scores and update the Discord embed. Handles premature match endings by switching to newer matches."""
        try:
            log.info(f"Starting score polling for match {initial_match_id}")
            message = self.live_messages.get(tracking_id)
            if not message:
                log.error(f"No message found for tracking ID {tracking_id}")
                return
            
            current_match_id = initial_match_id
            last_team1_score = -1
            last_team2_score = -1
            
            while tracking_id in self.live_messages:
                await asyncio.sleep(5)
                log.info(f"polling for match score updates for {current_match_id}")

                # Check if there's a newer match that started
                latest_match_id = await self.mysql_db.get_latest_match_id()
                if latest_match_id > current_match_id:
                    log.info(f"Newer match detected: {latest_match_id}, switching from {current_match_id}")
                    current_match_id = latest_match_id
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
                
                # Check if match is complete
                if map_data and self._check_if_complete_match(map_data, match_data):
                    log.info(f"Match {current_match_id} completed")
                    
                    # Final update with completed status
                    embed = discord.Embed(title="✅ Match Completed", color=discord.Color.green())
                    
                    if image_url:
                        embed.set_image(url=image_url)

                    embed.add_field(name="🏆 Final Score", value=f"{team1_score} - {team2_score}", inline=True)
                    winner = match_data.get('team1_name') if team1_score > team2_score else match_data.get('team2_name')
                    embed.add_field(name="👑 Winner", value=winner or 'Unknown', inline=True)
                    
                    await message.edit(embed=embed)

                    # TODO: Resolve bets here
                    break

                # Only update if scores changed
                if team1_score != last_team1_score or team2_score != last_team2_score:
                    embed = discord.Embed(title=f"Live Match Score: {team1_score} - {team2_score}", color=discord.Color.green())

                    if image_url:
                        embed.set_image(url=image_url)
                    
                    await message.edit(embed=embed)
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

    @tasks.loop(seconds=15)
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
    async def winrate(self, ctx: commands.Context):
        """Display win/loss records for all CS2 players"""
        try:
            player_records = await self.postgres_db.get_player_winrates()

            if not player_records:
                await ctx.send("No CS2 match data found.")
                return

            embed = discord.Embed(
                title="🏆 CS2 Player Win/Loss Records",
                color=discord.Color.green()
            )

            description = "```\n"
            description += f"{'Player':<20} {'Wins':<6} {'Losses':<6} {'WR%':<6}\n"
            description += "─" * 44 + "\n"

            for record in player_records:
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
