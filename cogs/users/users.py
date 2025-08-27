import discord
from discord.ext import commands
import logging
from .db import UsersDb
from bot import Zhenpai

log: logging.Logger = logging.getLogger(__name__)

class Users(commands.Cog):
    """Commands for managing users in the zhenpai system"""

    def __init__(self, bot: Zhenpai):
        self.bot = bot
        self.db = UsersDb(self.bot.db_pool)

    @commands.command()
    async def adduser(self, ctx: commands.Context, discord_id: int, discord_username: str, steamid64: int = None):
        """Add a new user to the system
        
        Usage: !adduser <discord_id> <discord_username> [steamid64]
        Example: !adduser 123456789 "username" 76561198012345678
        """
        try:
            # Check if user already exists
            existing_user = await self.db.get_user_by_discord_id(discord_id)
            
            if existing_user:
                # Update existing user
                user = await self.db.create_user(discord_id, discord_username, steamid64)
                await ctx.send(f"✅ Updated user **{discord_username}** (ID: {discord_id})" + 
                             (f" with Steam ID: {steamid64}" if steamid64 else ""))
            else:
                # Create new user
                user = await self.db.create_user(discord_id, discord_username, steamid64)
                await ctx.send(f"✅ Added new user **{discord_username}** (ID: {discord_id})" + 
                             (f" with Steam ID: {steamid64}" if steamid64 else ""))
                
        except Exception as e:
            log.error(f"Error adding user: {e}")
            await ctx.send(f"❌ Error adding user: {str(e)}")

    @commands.command()
    async def userinfo(self, ctx: commands.Context, discord_id: int):
        """Get information about a user
        
        Usage: !userinfo <discord_id>
        """
        try:
            user = await self.db.get_user_by_discord_id(discord_id)
            
            if user:
                embed = discord.Embed(title="User Information", color=discord.Color.blue())
                embed.add_field(name="Discord ID", value=user['discord_id'], inline=True)
                embed.add_field(name="Username", value=user['discord_username'], inline=True)
                embed.add_field(name="Steam ID", value=user['steamid64'] or "Not set", inline=True)
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ User with Discord ID {discord_id} not found")
                
        except Exception as e:
            log.error(f"Error getting user info: {e}")
            await ctx.send(f"❌ Error getting user info: {str(e)}")

    @commands.command()
    async def listusers(self, ctx: commands.Context):
        """List all users in the system"""
        try:
            users = await self.db.get_all_users()
            
            if users:
                embed = discord.Embed(title="All Users", color=discord.Color.green())
                
                for user in users:
                    steam_info = f"Steam: {user['steamid64']}" if user['steamid64'] else "No Steam ID"
                    embed.add_field(
                        name=f"{user['discord_username']} (ID: {user['discord_id']})", 
                        value=steam_info, 
                        inline=False
                    )
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("No users found in the system")
                
        except Exception as e:
            log.error(f"Error listing users: {e}")
            await ctx.send(f"❌ Error listing users: {str(e)}")

async def setup(bot: Zhenpai):
    await bot.add_cog(Users(bot))
