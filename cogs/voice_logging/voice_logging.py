import discord
from discord.ext import commands
import logging
from datetime import datetime
from typing import Optional

from bot import Zhenpai
from .db import VoiceLoggingDb

log: logging.Logger = logging.getLogger(__name__)

class VoiceLogging(commands.Cog):
    """Voice channel activity logging"""

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.db = VoiceLoggingDb(bot.db_pool)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice channel join/leave/move events"""
        if not member.guild:
            return

        # Get the log channel for this guild
        log_channel_id = await self.db.get_log_channel(member.guild.id)
        if not log_channel_id:
            return

        log_channel = self.bot.get_channel(log_channel_id)
        if not log_channel:
            return

        # Determine what happened
        embed = None
        
        if before.channel is None and after.channel is not None:
            # User joined a voice channel
            embed = discord.Embed(
                title="🎤 Voice Channel Joined",
                description=f"{member.mention} joined {after.channel.mention}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_author(name=member.display_name, icon_url=member.avatar.url if member.avatar else None)
            
        elif before.channel is not None and after.channel is None:
            # User left a voice channel
            embed = discord.Embed(
                title="🔇 Voice Channel Left",
                description=f"{member.mention} left {before.channel.mention}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.set_author(name=member.display_name, icon_url=member.avatar.url if member.avatar else None)
            
        elif before.channel != after.channel and before.channel is not None and after.channel is not None:
            # User moved between voice channels
            embed = discord.Embed(
                title="🔄 Voice Channel Moved",
                description=f"{member.mention} moved from {before.channel.mention} to {after.channel.mention}",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.set_author(name=member.display_name, icon_url=member.avatar.url if member.avatar else None)

        # Send the embed if we have one
        if embed:
            try:
                await log_channel.send(embed=embed)
            except Exception as e:
                log.error(f"Failed to send voice log message: {e}")

    @commands.group(name='voicelog', invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def voice_log(self, ctx):
        """Voice logging configuration commands"""
        await ctx.send("Available commands: `setup`, `disable`, `enable`")

    @voice_log.command(name='setup')
    @commands.has_permissions(manage_guild=True)
    async def setup_voice_log(self, ctx, channel: discord.TextChannel = None):
        """Set up voice logging for this server"""
        if channel is None:
            channel = ctx.channel

        await self.db.set_log_channel(ctx.guild.id, channel.id)
        
        embed = discord.Embed(
            title="✅ Voice Logging Configured",
            description=f"Voice channel activity will now be logged to {channel.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @voice_log.command(name='disable')
    @commands.has_permissions(manage_guild=True)
    async def disable_voice_log(self, ctx):
        """Disable voice logging for this server"""
        await self.db.disable_logging(ctx.guild.id)
        
        embed = discord.Embed(
            title="🔇 Voice Logging Disabled",
            description="Voice channel activity logging has been disabled",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    @voice_log.command(name='enable')
    @commands.has_permissions(manage_guild=True)
    async def enable_voice_log(self, ctx):
        """Enable voice logging for this server"""
        await self.db.enable_logging(ctx.guild.id)
        
        embed = discord.Embed(
            title="✅ Voice Logging Enabled",
            description="Voice channel activity logging has been enabled",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(VoiceLogging(bot))