from datetime import datetime, timezone
import discord
from discord.ext import commands, tasks
import logging

from cogs.users.db import UsersDb
from .db import PointsDb
from bot import Zhenpai

log: logging.Logger = logging.getLogger(__name__)

class Points(commands.Cog):
    """Commands for managing and betting points"""

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.db = PointsDb(self.bot.db_pool)
        self.user_db = UsersDb(self.bot.db_pool)

    async def cog_load(self):
        if not self.poll_events.is_running():
            self.poll_events.start()

    async def cog_unload(self):
        if self.poll_events.is_running():
            self.poll_events.cancel()

    @commands.command()
    async def points(self, ctx: commands.Context):
        """Gets the points leaderboard"""
        pass

    @commands.command()
    async def mypoints(self, ctx: commands.Context):
        """Displays the points history and total for this user"""
        pass

    @tasks.loop(minutes=1)
    async def poll_events(self):
        try:
            # Add different point sources here
            await self._process_cs2_matches()
            # await self._process_completed_bets()
            
            # TODO: update point_balances summation table here (why?)
        except Exception as e:
            log.error(f"Error in poll_events: {e}")

    async def _process_cs2_matches(self) -> None:
        matches = await self.db.fetch_unprocessed_cs2_matches()
        if not matches:
            return
        log.info(f"Found {len(matches)} unprocessed cs2 matches {','.join(str(m['matchid']) for m in matches)}")

        for match in matches:
            rows_to_add = []
            should_write = True
            matchid = match['matchid']
            winning_team = match['winner']
            player_stats = await self.db.get_match_players(matchid)
            for player in player_stats:
                points_earned = 1000
                points_earned += 250 if player['team_name'] == winning_team else 0
                points_earned += int(player['kills']) * 10
                points_earned += int(player['damage']) // 10

                # Build points table entry
                if (user := await self.user_db.get_user_by_steamid64(player['steamid64'])):
                    discord_id = user['discord_id']
                    change_value = points_earned
                    created_at = datetime.utcnow()
                    category = "cs2"
                    reason = "Played CS2"
                    event_source = "cs2_matches"
                    event_source_id = matchid

                    new_row = (discord_id, change_value, created_at, category, reason, event_source, event_source_id)
                    rows_to_add.append(new_row)
                else:
                    log.error(f"Could not find user for steamid64 {player['steamid64']}, aborting point rewarding")
                    should_write = False
                    break

            # add all the new points entries and mark event as processed
            if should_write:
                await self.db.perform_cs2_event_transaction(rows_to_add, matchid)

    @poll_events.before_loop
    async def before_poll_events(self):
        await self.bot.wait_until_ready()
        log.info(f"Starting {__name__} update loop")

    @poll_events.after_loop
    async def after_poll_events(self):
        log.info(f"Stopping {__name__} update loop")