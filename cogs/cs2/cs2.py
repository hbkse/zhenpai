import logging
import discord
from discord.ext import commands, tasks
from typing import List, Dict, Any, Optional, Tuple
from bot import Zhenpai
from .db import CS2MySQLDb, CS2PostgresDb

log: logging.Logger = logging.getLogger(__name__)

class CS2(commands.Cog):
    """ Counter-Strike 2 inhouse tracking for the friends """

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.mysql_db = CS2MySQLDb()
        self.postgres_db = CS2PostgresDb(bot.db_pool)
        self.last_processed_match_id = 0

    async def cog_load(self):
        """Initialize database connections and start polling task."""
        try:
            await self.mysql_db.connect()
            self.last_processed_match_id = await self.postgres_db.get_last_processed_match_id() or 0
            log.info(f"CS2 cog loaded. Last processed match ID: {self.last_processed_match_id}")
            
            # Start the polling task
            self.poll_matches.start()
        except Exception as e:
            log.error(f"Failed to initialize CS2 cog: {e}")

    async def cog_unload(self):
        """Clean up database connections and stop polling task."""
        self.poll_matches.cancel()
        await self.mysql_db.close()
        log.info("CS2 cog unloaded")

    def _check_if_complete_match(self, match: Dict[str, Any]):
        """
        Sometimes matchzy doesn't mark an end_time or winner for the match so we should base it off scores.
        """
        return match['team1_score'] or match['team2_score']

    @tasks.loop(minutes=1)
    async def poll_matches(self):
        """Poll MySQL for new matches every minute and replicate to PostgreSQL."""
        try:
            # Get new matches from MySQL
            new_matches = await self.mysql_db.get_matches_greater_than_matchid(self.last_processed_match_id)
            if not new_matches:
                log.info("No new matches found")
                return
            
            # Filter for complete matches in Python
            complete_matches = [match for match in new_matches if self._check_if_complete_match(match)]
            if not complete_matches:
                log.info("No complete matches found in new batch")
                return

            processed_count = 0
            for match in complete_matches:
                try:
                    matchid = match['matchid']
                    log.info(f"Processing matchid {matchid} for cs2 stats.")
                    maps_data = await self.mysql_db.get_map_stats_for_match(matchid)

                    # Process and insert match data
                    match_data = self._build_match_data(maps_data, match)
                    await self.postgres_db.insert_match(match_data)

                    # Process and insert player data
                    players_data = await self.mysql_db.get_player_stats_for_match(matchid)
                    match_players = [p for p in players_data if p['team'] != "Spectator"]
                    if len(match_players) != 10:
                        log.warning(f"Not 10 players for {matchid}")
                    for player in match_players:
                        await self.postgres_db.insert_player_data(player)
                    
                    processed_count += 1
                    self.last_processed_match_id = max(self.last_processed_match_id, match['matchid'])
                    
                except Exception as e:
                    log.error(f"Error processing match {match['matchid']}: {e}")
            
            if processed_count > 0:
                log.info(f"Successfully processed {processed_count} matches")
                
        except Exception as e:
            log.error(f"Error in poll_matches task: {e}")
    
    def _build_match_data(self, maps_data: Dict[str, Any], match_data: Dict[str, Any]):
        return {
            "matchid": maps_data['matchid'],
            "start_time": maps_data['start_time'],
            "end_time": maps_data['end_time'] or match_data['end_time'] or None, # this often doesnt write
            "winner": maps_data['winner'] or match_data['winner'] or None,
            "mapname": maps_data['mapname'],
            "team1_score": maps_data['team1_score'],
            "team2_score": maps_data['team2_score'],
            "team1_name": match_data['team1_name'],
            "team2_name": match_data['team2_name'],
        }

    @poll_matches.before_loop
    async def before_poll_matches(self):
        """Wait for bot to be ready before starting polling."""
        await self.bot.wait_until_ready()
        log.info("Starting CS2 match polling task")

    @commands.command(name="cs2")
    async def cs2_command(self, ctx: commands.Context):
        """Basic CS2 command placeholder."""
        await ctx.send("CS2 cog is working! 🎮")
