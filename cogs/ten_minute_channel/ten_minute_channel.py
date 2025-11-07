import logging
import discord
from discord.ext import tasks, commands
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple

from bot import Zhenpai
from .db import TenMinuteChannelDb

log: logging.Logger = logging.getLogger(__name__)

CHECK_INTERVAL_MINUTES = 1


class TenMinuteChannel(commands.Cog):
    """Manages channels where messages are automatically deleted after a configurable time period."""

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.db = TenMinuteChannelDb(bot.db_pool)
        # Store {(guild_id, channel_id): delete_after_minutes} in memory
        self.registered_channels: Dict[Tuple[int, int], int] = {}
        self.cleanup_messages.start()

    def cog_unload(self):
        self.cleanup_messages.cancel()

    @commands.command(name="create10min")
    @commands.has_permissions(manage_channels=True)
    async def create_ten_minute_channel(self, ctx: commands.Context, channel_name: str, delete_after_minutes: int = 10):
        """Create a new channel where messages are automatically deleted after a specified time.

        Usage: !create10min <channel_name> [delete_after_minutes]
        Example: !create10min quick-chat
        Example: !create10min urgent-matters 5
        """
        # Validate delete_after_minutes
        if delete_after_minutes < 1:
            await ctx.send("Delete period must be at least 1 minute.")
            return
        if delete_after_minutes > 1440:  # 24 hours
            await ctx.send("Delete period cannot exceed 1440 minutes (24 hours).")
            return

        try:
            # Create the new channel
            new_channel = await ctx.guild.create_text_channel(
                name=channel_name,
                category=ctx.channel.category if isinstance(ctx.channel, discord.TextChannel) else None,
                reason=f"Auto-delete channel created by {ctx.author}"
            )

            # Add to database
            await self.db.add_channel(ctx.guild.id, new_channel.id, delete_after_minutes)

            # Add to in-memory dict
            self.registered_channels[(ctx.guild.id, new_channel.id)] = delete_after_minutes

            await ctx.send(f"Created {new_channel.mention} with {delete_after_minutes}-minute message deletion enabled. Messages will be automatically deleted after {delete_after_minutes} minutes.")
            log.info(f"Created auto-delete channel {new_channel.id} ({channel_name}) with {delete_after_minutes} min period in guild {ctx.guild.id}")

        except discord.Forbidden:
            await ctx.send("I don't have permissions to create channels.")
        except Exception as e:
            await ctx.send(f"Error creating channel: {e}")
            log.error(f"Error creating auto-delete channel: {e}")

    @commands.command(name="delete10min")
    @commands.has_permissions(manage_channels=True)
    async def delete_ten_minute_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Delete an auto-delete channel.

        Usage: !delete10min #channel
        """
        channel_key = (ctx.guild.id, channel.id)

        # Check if it's a registered auto-delete channel
        if channel_key not in self.registered_channels:
            await ctx.send(f"{channel.mention} is not an auto-delete channel.")
            return

        try:
            # Remove from database
            await self.db.remove_channel(ctx.guild.id, channel.id)

            # Remove from in-memory dict
            del self.registered_channels[channel_key]

            # Delete the channel
            await channel.delete(reason=f"Auto-delete channel deleted by {ctx.author}")

            await ctx.send(f"Deleted auto-delete channel: {channel.name}")
            log.info(f"Deleted auto-delete channel {channel.id} ({channel.name}) in guild {ctx.guild.id}")

        except discord.Forbidden:
            await ctx.send("I don't have permissions to delete that channel.")
        except Exception as e:
            await ctx.send(f"Error deleting channel: {e}")
            log.error(f"Error deleting auto-delete channel: {e}")

    @commands.command(name="list10min")
    @commands.has_permissions(manage_channels=True)
    async def list_ten_minute_channels(self, ctx: commands.Context):
        """List all auto-delete channels in this server."""
        guild_channels = [
            ((guild_id, channel_id), minutes)
            for (guild_id, channel_id), minutes in self.registered_channels.items()
            if guild_id == ctx.guild.id
        ]

        if not guild_channels:
            await ctx.send("No auto-delete channels in this server.")
            return

        channel_info = []
        for (_, channel_id), minutes in guild_channels:
            channel = self.bot.get_channel(channel_id)
            if channel:
                channel_info.append(f"{channel.mention} - {minutes} minute{'s' if minutes != 1 else ''}")
            else:
                channel_info.append(f"<Unknown channel {channel_id}> - {minutes} minute{'s' if minutes != 1 else ''}")

        await ctx.send(f"Auto-delete channels:\n" + "\n".join(channel_info))

    @commands.command(name="configure10min")
    @commands.has_permissions(manage_channels=True)
    async def configure_deletion_period(self, ctx: commands.Context, channel: discord.TextChannel, delete_after_minutes: int):
        """Configure the deletion period for an auto-delete channel.

        Usage: !configure10min #channel <minutes>
        Example: !configure10min #quick-chat 5
        """
        channel_key = (ctx.guild.id, channel.id)

        # Check if it's a registered auto-delete channel
        if channel_key not in self.registered_channels:
            await ctx.send(f"{channel.mention} is not an auto-delete channel.")
            return

        # Validate delete_after_minutes
        if delete_after_minutes < 1:
            await ctx.send("Delete period must be at least 1 minute.")
            return
        if delete_after_minutes > 1440:  # 24 hours
            await ctx.send("Delete period cannot exceed 1440 minutes (24 hours).")
            return

        try:
            # Update in database
            await self.db.update_delete_after_minutes(ctx.guild.id, channel.id, delete_after_minutes)

            # Update in-memory dict
            self.registered_channels[channel_key] = delete_after_minutes

            await ctx.send(f"Updated {channel.mention} to delete messages after {delete_after_minutes} minute{'s' if delete_after_minutes != 1 else ''}.")
            log.info(f"Updated auto-delete period for channel {channel.id} to {delete_after_minutes} minutes in guild {ctx.guild.id}")

        except Exception as e:
            await ctx.send(f"Error updating channel configuration: {e}")
            log.error(f"Error updating auto-delete channel configuration: {e}")

    @tasks.loop(minutes=CHECK_INTERVAL_MINUTES)
    async def cleanup_messages(self):
        """Poll registered channels and delete messages older than their configured deletion period."""
        # Use in-memory dict instead of fetching from database
        for (guild_id, channel_id), delete_after_minutes in list(self.registered_channels.items()):
            channel = self.bot.get_channel(channel_id)

            if not channel:
                log.warning(f"Channel {channel_id} not found, removing from registered channels")
                del self.registered_channels[(guild_id, channel_id)]
                await self.db.remove_channel(guild_id, channel_id)
                continue

            # Calculate cutoff time based on channel's configured deletion period
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=delete_after_minutes)

            try:
                messages_to_delete = []

                # Fetch messages and check their age
                async for message in channel.history(limit=100):
                    if message.created_at < cutoff_time:
                        messages_to_delete.append(message)

                if messages_to_delete:
                    # Discord bulk delete only works for messages less than 14 days old
                    # and requires at least 2 messages
                    if len(messages_to_delete) == 1:
                        await messages_to_delete[0].delete()
                        log.info(f"Deleted 1 message from channel {channel_id}")
                    else:
                        # Filter out messages older than 14 days for bulk delete
                        fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
                        bulk_delete = [m for m in messages_to_delete if m.created_at > fourteen_days_ago]
                        old_delete = [m for m in messages_to_delete if m.created_at <= fourteen_days_ago]

                        if bulk_delete:
                            await channel.delete_messages(bulk_delete)
                            log.info(f"Bulk deleted {len(bulk_delete)} messages from channel {channel_id}")

                        # Delete very old messages individually
                        for message in old_delete:
                            await message.delete()
                            log.info(f"Individually deleted old message from channel {channel_id}")

            except discord.Forbidden:
                log.error(f"Missing permissions to delete messages in channel {channel_id}")
            except Exception as e:
                log.error(f"Error cleaning up messages in channel {channel_id}: {e}")

    @cleanup_messages.before_loop
    async def before_cleanup_messages(self):
        await self.bot.wait_until_ready()

        # Load registered channels from database into memory
        channels = await self.db.get_all_channels()
        for record in channels:
            self.registered_channels[(record.guild_id, record.channel_id)] = record.delete_after_minutes
        log.info(f"Loaded {len(self.registered_channels)} registered channels from database")

        log.info(f"Starting {__name__} cleanup loop")

    @cleanup_messages.after_loop
    async def after_cleanup_messages(self):
        log.info(f"Stopping {__name__} cleanup loop")
