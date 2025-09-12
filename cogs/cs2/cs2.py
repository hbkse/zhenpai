import asyncio
from aiohttp import web
from datetime import datetime
from config import LIVE_MATCH_CHANNEL_ID, GUELO_TEAMS_JSON_URL
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
        await self.mysql_db.close()
        log.info("CS2 cog unloaded")

    async def start_live_tracking(self, request):
        try:
            # Parse image URL from request
            request_data = {}
            if request.content_type == 'application/json':
                request_data = await request.json()
            image_url = request_data.get('image_url')
            
            channel = self.bot.get_channel(LIVE_MATCH_CHANNEL_ID)
            if channel:
                # await channel.send("start_live_tracking entry")
                
                # Create embed with image as the center piece
                embed = discord.Embed(title="Inhouse starting soon!", color=discord.Color.yellow())
                
                if image_url:
                    embed.set_image(url=image_url)
                else:
                    log.warning("didn't get image_url")

                async with self.bot.http_client.get(GUELO_TEAMS_JSON_URL) as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        await channel.send(str(data))
                        # Add match data to embed
                        mapname = data['maplist'][0] or "Unknown"
                        mapside = data['map_sides'][0] or "Unknown"
                        embed.add_field(name="🗺️ Map", value=mapname, inline=True)
                        embed.add_field(name="🔄 Side", value=mapside, inline=True)
                        
                        message = await channel.send(embed=embed)
                    else:
                        log.warning(f"Failed to fetch from {GUELO_TEAMS_JSON_URL} guelo teams json: {resp.status}")
                        # If no match data available, still send embed with image
                        message = await channel.send(embed=embed)

            return web.Response(text='')
        except Exception as e:
            print(f"Discord action error: {e}")
            return web.Response(text='Error', status=500)

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
