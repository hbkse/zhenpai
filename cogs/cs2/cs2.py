import logging
import discord
from discord.ext import commands
from bot import Zhenpai
from .db import CS2MySQLDatabase

log: logging.Logger = logging.getLogger(__name__)

class CS2(commands.Cog):
    """ Counter-Strike 2 inhouse bot functionality
    """

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.db = CS2MySQLDatabase()

    async def cog_load(self):
        """Initialize database connection when cog loads."""
        try:
            await self.db.connect()
            log.info("CS2 cog loaded and database connected")
        except Exception as e:
            log.error(f"Failed to connect to CS2 database: {e}")

    async def cog_unload(self):
        """Clean up database connection when cog unloads."""
        await self.db.close()
        log.info("CS2 cog unloaded and database disconnected")

    @commands.command(name="cs2")
    async def cs2_command(self, ctx: commands.Context):
        """ Basic CS2 command placeholder. """
        await ctx.send("CS2 cog is working! 🎮")

    @commands.command(name="cs2tables")
    async def list_tables(self, ctx: commands.Context):
        """List all tables in the CS2 database."""
        try:
            tables = await self.db.get_all_tables()
            if tables:
                table_list = "\n".join([f"• {table}" for table in tables])
                embed = discord.Embed(
                    title="CS2 Database Tables",
                    description=f"Found {len(tables)} table(s):\n{table_list}",
                    color=discord.Color.blue()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("No tables found in the database.")
        except Exception as e:
            await ctx.send(f"Error accessing database: {str(e)}")

    @commands.command(name="cs2schema")
    async def show_schema(self, ctx: commands.Context, table_name: str):
        """Show the schema of a specific table."""
        try:
            schema = await self.db.get_table_schema(table_name)
            if schema:
                schema_text = "\n".join([
                    f"• **{col['field']}** - {col['type']} ({'NULL' if col['null'] == 'YES' else 'NOT NULL'})"
                    for col in schema
                ])
                embed = discord.Embed(
                    title=f"Schema for table: {table_name}",
                    description=schema_text,
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Table '{table_name}' not found or has no columns.")
        except Exception as e:
            await ctx.send(f"Error getting schema: {str(e)}")

    @commands.command(name="cs2data")
    async def show_data(self, ctx: commands.Context, table_name: str, limit: int = 10):
        """Show data from a specific table (default limit: 10 rows)."""
        if limit > 50:
            await ctx.send("Limit cannot exceed 50 rows for safety.")
            return
        
        try:
            data = await self.db.get_table_data(table_name, limit)
            count = await self.db.get_table_count(table_name)
            
            if data:
                # Create a formatted display of the data
                if len(data) > 0:
                    # Get column names from first row
                    columns = list(data[0].keys())
                    
                    # Create a table-like display
                    table_text = " | ".join(columns) + "\n"
                    table_text += "-" * len(table_text) + "\n"
                    
                    for row in data[:5]:  # Show first 5 rows in message
                        row_values = [str(row.get(col, ''))[:20] for col in columns]  # Truncate long values
                        table_text += " | ".join(row_values) + "\n"
                    
                    if len(data) > 5:
                        table_text += f"\n... and {len(data) - 5} more rows"
                    
                    embed = discord.Embed(
                        title=f"Data from {table_name}",
                        description=f"Showing {len(data)} of {count} total rows:\n```\n{table_text}\n```",
                        color=discord.Color.orange()
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"Table '{table_name}' is empty.")
            else:
                await ctx.send(f"Table '{table_name}' not found or has no data.")
        except Exception as e:
            await ctx.send(f"Error getting data: {str(e)}")

    @commands.command(name="cs2count")
    async def show_count(self, ctx: commands.Context, table_name: str):
        """Show the total number of rows in a table."""
        try:
            count = await self.db.get_table_count(table_name)
            embed = discord.Embed(
                title=f"Row count for {table_name}",
                description=f"Total rows: **{count}**",
                color=discord.Color.purple()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Error getting count: {str(e)}")
