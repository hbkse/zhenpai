from datetime import datetime, timezone
import discord
from discord.ext import commands, tasks
from discord import app_commands
from config import CS2_POINTS_GRAPH_URL
import logging
import os
import asyncio

from cogs.users.db import UsersDb
from .db import PointsDb
from bot import Zhenpai

log: logging.Logger = logging.getLogger(__name__)

class Points(commands.Cog):
    """Commands for managing and betting points"""

    FOOTER_MESSAGE = "!p | !p @user | !leaderboard | Try /points |"

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
    async def leaderboard(self, ctx: commands.Context):
        """Gets the points leaderboard"""

        # Send loading embed first
        loading_embed = discord.Embed(
            title="🏆 Points Leaderboard",
            description="🔄 Loading leaderboard data...",
            color=0xffd700,  # Gold color
            timestamp=datetime.utcnow()
        )
        loading_embed.set_footer(text="!leaderboard !points !points @user !points table !p !mp")
        
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

        embed.set_footer(text=self.FOOTER_MESSAGE)

        await message.edit(embed=embed)

    @commands.command(aliases=['p', 'mp', 'mypoints'])
    async def points(self, ctx: commands.Context, user: discord.Member = None, *, view_type: str = "graph"):
        """Displays the points history and total for this user"""
        if user is None:
            user = ctx.author

        if view_type.lower() == "table":
            await self.points_table(ctx, user)
        else:
            await self.points_graph(ctx, user)

    async def points_graph(self, ctx: commands.Context, user: discord.Member):
        """Display points with graph view"""
        total = await self.db.get_total_points_by_discord_id(user.id)

        # Create embed
        embed = discord.Embed(
            title=f"💰 Total Points: **{total:,}**",
            color=0x00ff00 if total > 0 else 0xff6b6b,  # Green if positive, red-ish if zero/negative
        )
        
        # Add user info
        embed.set_author(
            name=user.display_name,
            icon_url=user.avatar.url if user.avatar else None
        )
        
        # Add main image at bottom of embed
        if CS2_POINTS_GRAPH_URL:
            timestamp = int(datetime.now(timezone.utc).timestamp())
            full_url = f"{CS2_POINTS_GRAPH_URL}/user-points?discord_id={user.id}&t={timestamp}"
            log.info(f"Loading points graph from: {full_url}")
            embed.set_image(url=full_url)

        embed.set_footer(text=self.FOOTER_MESSAGE)

        await ctx.send(embed=embed)

    @app_commands.command(name="points", description="View your points balance and history")
    @app_commands.describe(
        user="The user to check points for (defaults to yourself)",
        view_type="Display type: 'graph' (default) or 'table'"
    )
    @app_commands.choices(view_type=[
        app_commands.Choice(name="Graph", value="graph"),
        app_commands.Choice(name="Table", value="table")
    ])
    async def points_slash(self, interaction: discord.Interaction, user: discord.Member = None, view_type: str = "graph"):
        """Slash command version of !points with ephemeral response"""
        if user is None:
            user = interaction.user
        
        # Create a mock context object for reusing existing methods
        class MockContext:
            def __init__(self, interaction):
                self.author = interaction.user
                self.guild = interaction.guild
                self.channel = interaction.channel
                self._interaction = interaction
                self._responded = False
            
            async def send(self, **kwargs):
                if not self._responded:
                    await self._interaction.response.send_message(ephemeral=True, **kwargs)
                    self._responded = True
                else:
                    await self._interaction.followup.send(ephemeral=True, **kwargs)
        
        mock_ctx = MockContext(interaction)
        
        if view_type.lower() == "table":
            await self.points_table(mock_ctx, user)
        else:
            await self.points_graph(mock_ctx, user)

    async def points_table(self, ctx: commands.Context, user: discord.Member):
        """Display points with table view"""
        total = await self.db.get_total_points_by_discord_id(user.id)
        history = await self.db.get_recent_points_transactions_by_discord_id(user.id)

        # Create embed
        embed = discord.Embed(
            title=f"💰 Total Points: **{total:,}**",
            color=0x00ff00 if total > 0 else 0xff6b6b,  # Green if positive, red-ish if zero/negative
        )
        
        # Add user info
        embed.set_author(
            name=user.display_name,
            icon_url=user.avatar.url if user.avatar else None
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

        embed.set_footer(text=self.FOOTER_MESSAGE)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def rewardpoints(self, ctx: commands.Context, user: discord.User, amount: int, *, reason: str):
        """Manually reward or remove points from a user (Admin only)
        
        Usage: !rewardpoints @user 100 Great performance in tournament
               !rewardpoints @user -50 Rule violation penalty
        """
        try:
            # Validate inputs
            if abs(amount) > 100000:  # Sanity check to prevent extreme values
                await ctx.send("❌ Amount must be between -100,000 and 100,000 points.")
                return
            
            if len(reason) > 255:  # Reasonable limit for reason length
                await ctx.send("❌ Reason must be 255 characters or less.")
                return
            
            # Add the points reward/penalty to the database
            await self.db.add_points_reward(user.id, amount, reason)
            
            # Get updated total for the user
            new_total = await self.db.get_total_points_by_discord_id(user.id)
            
            # Create confirmation embed
            action = "rewarded" if amount > 0 else "deducted"
            emoji = "💰" if amount > 0 else "💸"
            color = 0x00ff00 if amount > 0 else 0xff6b6b
            
            embed = discord.Embed(
                title=f"{emoji} Points {action.capitalize()}",
                description=f"**{amount:+,}** points {action} {'to' if amount > 0 else 'from'} {user.display_name}",
                color=color,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="📝 Reason",
                value=reason,
                inline=False
            )
            
            embed.add_field(
                name="📊 New Total",
                value=f"{new_total:,} points",
                inline=True
            )
            
            embed.add_field(
                name="👤 User",
                value=user.mention,
                inline=True
            )
            
            embed.add_field(
                name="🛡️ Admin",
                value=ctx.author.mention,
                inline=True
            )
            
            embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
            embed.set_footer(text="Admin Reward")
            
            await ctx.send(embed=embed)
            log.info(f"Admin {ctx.author.id} rewarded {amount} points to user {user.id} for reason: {reason}")
            
        except Exception as e:
            log.error(f"Error in rewardpoints command: {e}")
            await ctx.send("❌ An error occurred while processing the points reward. Please try again.")

    @commands.command()
    @commands.is_owner()
    async def rewardbulk(self, ctx: commands.Context, *, bulk_data: str):
        """Bulk reward points based on win/loss format (Admin only)

        Expected format:
        ```
        win
        79190764512350208 15000
        111679644054351872 10000

        loss
        98560137010106368 5000
        ```

        Win entries get positive points, loss entries get negative points.
        """
        try:
            # Extract content from markdown code blocks
            bulk_data = bulk_data.strip()
            if bulk_data.startswith('```') and bulk_data.endswith('```'):
                # Remove the ``` markers and any language specifier
                lines = bulk_data[3:-3].strip().split('\n')
                # Remove language specifier if present (e.g., ```markdown)
                if lines and not lines[0].strip():
                    lines = lines[1:]
                elif lines and lines[0].strip() and not any(char.isdigit() for char in lines[0]) and 'win' not in lines[0].lower() and 'loss' not in lines[0].lower():
                    lines = lines[1:]  # Remove language specifier line
            else:
                lines = bulk_data.split('\n')

            rewards = []
            current_multiplier = 1
            processed_count = 0
            errors = []

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue

                # Check for win/loss indicators
                if line.lower() == 'win':
                    current_multiplier = 1
                    continue
                elif line.lower() == 'loss':
                    current_multiplier = -1
                    continue

                # Parse user ID and points
                parts = line.split()
                if len(parts) != 2:
                    errors.append(f"Line {line_num}: Invalid format - expected 'user_id points'")
                    continue

                try:
                    user_id = int(parts[0])
                    base_points = int(parts[1])
                    final_points = base_points * current_multiplier

                    # Validate user exists
                    try:
                        user = await ctx.bot.fetch_user(user_id)
                        rewards.append((user, final_points))
                        processed_count += 1
                    except discord.NotFound:
                        errors.append(f"Line {line_num}: User {user_id} not found")
                        continue

                except ValueError:
                    errors.append(f"Line {line_num}: Invalid numbers - '{line}'")
                    continue

            if not rewards and not errors:
                await ctx.send("❌ No valid entries found. Please check your format.")
                return

            # Show preview and ask for confirmation
            preview_embed = discord.Embed(
                title="🔍 Bulk Reward Preview",
                description=f"Found {len(rewards)} valid entries to process",
                color=0xffa500,
                timestamp=datetime.utcnow()
            )

            preview_text = ""
            for user, points in rewards[:10]:  # Show first 10
                action = "+" if points > 0 else ""
                preview_text += f"{user.display_name}: {action}{points:,} points\n"

            if len(rewards) > 10:
                preview_text += f"... and {len(rewards) - 10} more entries"

            preview_embed.add_field(
                name="📊 Changes",
                value=preview_text or "None",
                inline=False
            )

            if errors:
                error_text = "\n".join(errors[:5])
                if len(errors) > 5:
                    error_text += f"\n... and {len(errors) - 5} more errors"
                preview_embed.add_field(
                    name="⚠️ Errors",
                    value=error_text,
                    inline=False
                )

            preview_embed.set_footer(text="React with ✅ to confirm or ❌ to cancel")

            message = await ctx.send(embed=preview_embed)
            await message.add_reaction("✅")
            await message.add_reaction("❌")

            def check(reaction, user):
                return (user == ctx.author and
                       str(reaction.emoji) in ["✅", "❌"] and
                       reaction.message.id == message.id)

            try:
                reaction, user = await ctx.bot.wait_for('reaction_add', timeout=30.0, check=check)

                if str(reaction.emoji) == "❌":
                    await ctx.send("❌ Bulk reward cancelled.")
                    return

                # Process all rewards
                successful = 0
                failed = 0
                results = []

                for user, points in rewards:
                    try:
                        reason = "Won CS2 Bet" if points > 0 else "Lost CS2 Bet"
                        await self.db.add_points_reward(user.id, points, reason)

                        # Get updated total for this user
                        new_total = await self.db.get_total_points_by_discord_id(user.id)
                        results.append((user, points, new_total))
                        successful += 1
                    except Exception as e:
                        log.error(f"Failed to reward {points} points to user {user.id}: {e}")
                        failed += 1

                # Send final confirmation
                result_embed = discord.Embed(
                    title="✅ Bulk Reward Complete",
                    description=f"Successfully processed {successful} entries",
                    color=0x00ff00,
                    timestamp=datetime.utcnow()
                )

                # Show detailed results
                if results:
                    results_text = ""
                    for user, points, new_total in results:
                        action = "+" if points > 0 else ""
                        results_text += f"**{user.display_name}**: {action}{points:,} → {new_total:,} total\n"

                    # Split into multiple fields if too long
                    if len(results_text) > 1024:
                        # Split results into chunks
                        chunks = []
                        current_chunk = ""
                        for user, points, new_total in results:
                            action = "+" if points > 0 else ""
                            line = f"**{user.display_name}**: {action}{points:,} → {new_total:,} total\n"
                            if len(current_chunk + line) > 1024:
                                chunks.append(current_chunk)
                                current_chunk = line
                            else:
                                current_chunk += line
                        if current_chunk:
                            chunks.append(current_chunk)

                        for i, chunk in enumerate(chunks):
                            field_name = "📊 Results" if i == 0 else f"📊 Results (cont. {i+1})"
                            result_embed.add_field(
                                name=field_name,
                                value=chunk,
                                inline=False
                            )
                    else:
                        result_embed.add_field(
                            name="📊 Results",
                            value=results_text,
                            inline=False
                        )

                if failed > 0:
                    result_embed.add_field(
                        name="⚠️ Failed",
                        value=f"{failed} entries failed to process",
                        inline=True
                    )

                result_embed.add_field(
                    name="🛡️ Admin",
                    value=ctx.author.mention,
                    inline=True
                )

                await ctx.send(embed=result_embed)
                log.info(f"Admin {ctx.author.id} completed bulk reward: {successful} successful, {failed} failed")

            except asyncio.TimeoutError:
                await ctx.send("❌ Confirmation timeout. Bulk reward cancelled.")

        except Exception as e:
            log.error(f"Error in rewardbulk command: {e}")
            await ctx.send("❌ An error occurred while processing the bulk reward. Please try again.")

    @commands.command(aliases=['give'])
    async def givepoints(self, ctx: commands.Context, user: discord.Member, amount: int):
        """Give some of your points to another user
        
        Usage: !givepoints @user 100
               !give @user 50
        """
        try:
            # Validate inputs
            if amount <= 0:
                await ctx.send("❌ Amount must be positive.")
                return
            
            if amount > 100000:  # Sanity check to prevent extreme values
                await ctx.send("❌ Amount must be 100,000 points or less.")
                return
            
            if user.id == ctx.author.id:
                await ctx.send("❌ You can't give points to yourself.")
                return
            
            # Check if sender has enough points
            sender_balance = await self.db.get_total_points_by_discord_id(ctx.author.id)
            if sender_balance < amount:
                await ctx.send(f"❌ Insufficient points. You have {sender_balance:,} points, but need {amount:,}.")
                return
            
            # Perform the transfer
            await self.db.transfer_points(
                ctx.author.id, 
                user.id, 
                amount, 
                ctx.author.display_name, 
                user.display_name
            )
            
            # Get updated balances
            sender_new_balance = await self.db.get_total_points_by_discord_id(ctx.author.id)
            receiver_new_balance = await self.db.get_total_points_by_discord_id(user.id)
            
            # Create confirmation embed
            embed = discord.Embed(
                title="💸 Points Transfer Complete",
                description=f"**{amount:,}** points transferred from {ctx.author.display_name} to {user.display_name}",
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="📤 From",
                value=f"{ctx.author.mention}\nNew balance: {sender_new_balance:,}",
                inline=True
            )
            
            embed.add_field(
                name="📥 To", 
                value=f"{user.mention}\nNew balance: {receiver_new_balance:,}",
                inline=True
            )
            
            embed.add_field(
                name="💰 Amount",
                value=f"{amount:,} points",
                inline=True
            )
            
            embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)
            embed.set_footer(text="!givepoints @user <amount> or !give @user <amount>")
            
            await ctx.send(embed=embed)
            log.info(f"User {ctx.author.id} transferred {amount} points to user {user.id}")
            
        except Exception as e:
            log.error(f"Error in givepoints command: {e}")
            await ctx.send("❌ An error occurred while processing the points transfer. Please try again.")

    @givepoints.error
    async def givepoints_error(self, ctx: commands.Context, error):
        """Handle errors for the givepoints command"""
        if isinstance(error, commands.UserNotFound):
            await ctx.send("❌ User not found. Please mention a valid user.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid arguments. Usage: `!givepoints @user <amount>`")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Missing required arguments. Usage: `!givepoints @user <amount>`")
        else:
            log.error(f"Unexpected error in givepoints command: {error}")
            await ctx.send("❌ An unexpected error occurred.")

    @rewardpoints.error
    async def rewardpoints_error(self, ctx: commands.Context, error):
        """Handle errors for the rewardpoints command"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need administrator permissions to use this command.")
        elif isinstance(error, commands.UserNotFound):
            await ctx.send("❌ User not found. Please mention a valid user.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid arguments. Usage: `!rewardpoints @user <amount> <reason>`")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Missing required arguments. Usage: `!rewardpoints @user <amount> <reason>`")
        else:
            log.error(f"Unexpected error in rewardpoints command: {error}")
            await ctx.send("❌ An unexpected error occurred.")

    @rewardbulk.error
    async def rewardbulk_error(self, ctx: commands.Context, error):
        """Handle errors for the rewardbulk command"""
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ You need to be the bot owner to use this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Missing bulk data. Usage: `!rewardbulk <bulk_data>`\n"
                          "Expected format:\n```\nwin\n79190764512350208 15000\n111679644054351872 10000\n\n"
                          "loss\n98560137010106368 5000\n```")
        else:
            log.error(f"Unexpected error in rewardbulk command: {error}")
            await ctx.send("❌ An unexpected error occurred.")

    @tasks.loop(seconds=15)
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