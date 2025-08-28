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

        # Send loading embed first
        loading_embed = discord.Embed(
            title="🏆 Points Leaderboard",
            description="🔄 Loading leaderboard data...",
            color=0xffd700,  # Gold color
            timestamp=datetime.utcnow()
        )
        loading_embed.set_footer(text="!points !mypoints")
        
        # Send the loading message
        message = await ctx.send(embed=loading_embed)

        # this is a table scan so it could take a while
        leaderboard = await self.db.get_points_leaderboard()
        
        if not leaderboard:
            embed = discord.Embed(
                title="🏆 Points Leaderboard",
                description="No points data found!",
                color=0xff6b6b
            )
            await message.edit(embed=embed)
            return
        
        # Create embed
        embed = discord.Embed(
            title="🏆 Points Leaderboard",
            description="Top players by total points earned",
            color=0xffd700,  # Gold color
            timestamp=datetime.utcnow()
        )
        
        # Medal emojis for top 3
        medals = ["🥇", "🥈", "🥉"]
        
        leaderboard_text = ""
        
        for i, record in enumerate(leaderboard):
            # Get Discord user object to fetch username and avatar
            try:
                user = await ctx.bot.fetch_user(record['discord_id'])
                username = user.display_name
            except:
                # Fallback if user not found
                username = f"User#{record['discord_id']}"
            
            # Format position with medal or number
            if i < 3:
                position = medals[i]
            else:
                position = f"`#{i+1:2d}`"
            
            # Format points with commas
            points_formatted = f"{record['total_points']:,}"
            
            # Add to leaderboard text
            leaderboard_text += f"{position} **{username}** - `{points_formatted}` points\n"
        
        embed.add_field(
            name="📊 Rankings",
            value=leaderboard_text,
            inline=False
        )
        
        # Set thumbnail to the top user's avatar if available
        if leaderboard:
            try:
                top_user = await ctx.bot.fetch_user(leaderboard[0]['discord_id'])
                if top_user.avatar:
                    embed.set_thumbnail(url=top_user.avatar.url)
            except:
                pass
        
        embed.set_footer(text="!points !mypoints")
        
        await message.edit(embed=embed)

    @commands.command()
    async def mypoints(self, ctx: commands.Context):
        """Displays the points history and total for this user"""
        total = await self.db.get_total_points_by_discord_id(ctx.message.author.id)
        history = await self.db.get_recent_points_transactions_by_discord_id(ctx.message.author.id)

        # Create embed
        embed = discord.Embed(
            title=f"💰 Total Points: **{total:,}**",
            color=0x00ff00 if total > 0 else 0xff6b6b,  # Green if positive, red-ish if zero/negative
        )
        
        # Add user info
        embed.set_author(
            name=ctx.message.author.display_name,
            icon_url=ctx.message.author.avatar.url if ctx.message.author.avatar else None
        )
        
        # History section
        if history:
            # Create table header
            history_text = "```\n"
            history_text += "Date       | Points  | Category | Reason\n"
            history_text += "-" * 50 + "\n"
            
            # Add each transaction (limit to prevent embed overflow)
            display_limit = min(10, len(history))  # Show max 10 transactions
            
            for record in history[:display_limit]:
                # Format date to be more readable
                date_str = record['created_at'].strftime("%m/%d %H:%M")
                
                # Format points with + or - sign and commas
                points_str = f"+{record['change_value']:,}" if record['change_value'] > 0 else f"{record['change_value']:,}"
                
                # Truncate long reasons to fit
                reason = record['reason'][:15] + "..." if len(record['reason']) > 15 else record['reason']
                category = record['category'][:8]  # Limit category length
                
                history_text += f"{date_str:<10} | {points_str:>7} | {category:<8} | {reason}\n"
            
            history_text += "```"
            
            embed.add_field(
                # name=f"📈 History ({display_limit} of {len(history)})",
                name=f"📈 History",
                value=history_text,
                inline=False
            )
        else:
            embed.add_field(
                name="📈 History",
                value="No points history found.",
                inline=False
            )
        embed.set_footer(text="!points !mypoints")
        
        await ctx.send(embed=embed)

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
                    created_at = match['start_time']
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