import discord
from discord.ext import commands
import logging
import subprocess
import config
import datetime
from bot import Zhenpai

from typing import Optional

log: logging.Logger = logging.getLogger(__name__)

class Admin(commands.Cog):
    """Admin commands for managing the bot"""

    def __init__(self, bot: Zhenpai):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def debug(self, ctx: commands.Context):
        message = [
            f'Logged in as: {self.bot.user}',
            f'Discord.py version: {discord.__version__}',
            f'Commit hash: {config.COMMIT_HASH}',
            f'Server time: {datetime.datetime.now()}',
            f'Bot uptime: {datetime.datetime.now() - self.bot.start_time}'
        ]
        log.info("Debug command used.")

        await ctx.send("\n".join(message))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def servers(self, ctx: commands.Context):
        servers = "\n".join([f"{guild.name} ({guild.id})" for guild in self.bot.guilds])
        await ctx.send(servers)

    @commands.command(aliases=['rlc'], hidden=True)
    @commands.is_owner()
    async def load_cog(self, ctx: commands.Context, ext: str):
        """Reload cog really useful for development."""

        if ext in self.bot.extensions:
            await self.bot.reload_extension(ext)
        else:
            await self.bot.load_extension(ext)
        log.info('Loaded extension: %s', ext)
        await ctx.send(f"{ext} successfully loaded.")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unload_cog(self, ctx: commands.Context, ext: str):
        await self.bot.unload_extension(ext)
        log.info('Unloaded extension: %s', ext)
        await ctx.send(f"{ext} successfully unloaded.")
    
    @commands.command(hidden=True)
    @commands.is_owner()
    async def change_status(self, ctx: commands.Context, message: str):
        game = discord.Game(name=message)
        await self.bot.change_presence(activity=game)
        await ctx.send("Status successfully changed.")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def logs(self, ctx: commands.Context, lines: Optional[int]):
        num_lines = str(lines) if lines else '20'

        try:
            logs = subprocess.check_output(['tail', '-n', num_lines, 'info.log'], stderr=subprocess.STDOUT)
            logs_str = logs.decode('utf-8')
            # yaml formatting for some random colorations :shrug:
            await ctx.send(f'```yaml\n{logs_str}```')
        except subprocess.CalledProcessError as e:
            await ctx.send(f'Error retrieving logs: {e.output.decode("utf-8")}')


    @commands.group(invoke_without_command=True, hidden=True)
    @commands.is_owner()
    @commands.guild_only()
    async def sync(self, ctx: commands.Context, guild_id: Optional[int], copy: bool = False) -> None:
        """Syncs the slash commands with the given guild"""

        if guild_id:
            guild = discord.Object(id=guild_id)
        else:
            guild = ctx.guild

        if copy:
            self.bot.tree.copy_global_to(guild=guild)

        commands = await self.bot.tree.sync(guild=guild)
        await ctx.send(f'Successfully synced {len(commands)} commands')

    @sync.command(name='global')
    @commands.is_owner()
    async def sync_global(self, ctx: commands.Context):
        """Syncs the commands globally"""

        commands = await self.bot.tree.sync(guild=None)
        await ctx.send(f'Successfully synced {len(commands)} commands')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def drop_table(self, ctx: commands.Context, table_name: str):
        """Drop all data from a specified table."""
        try:
            # Validate table name to prevent SQL injection
            allowed_tables = {
                'cs2_matches', 'cs2_player_stats', 'users', 'points', 'processed_events'
            }
            
            if table_name.lower() not in allowed_tables:
                await ctx.send(f"❌ Table '{table_name}' is not in the allowed list. Allowed tables: {', '.join(allowed_tables)}")
                return
            
            # Get the database pool from the bot
            if not hasattr(self.bot, 'db_pool') or not self.bot.db_pool:
                await ctx.send("❌ Database pool not available.")
                return
            
            # Delete all records from the specified table
            query = f"DELETE FROM {table_name}"
            await self.bot.db_pool.execute(query)
            
            await ctx.send(f"✅ Successfully dropped all data from {table_name} table.")
            log.info(f"Admin {ctx.author} dropped all data from {table_name} table")
            
        except Exception as e:
            await ctx.send(f"❌ Error dropping data from {table_name}: {e}")
            log.error(f"Error dropping data from {table_name}: {e}")

async def setup(bot: Zhenpai):
    await bot.add_cog(Admin(bot))