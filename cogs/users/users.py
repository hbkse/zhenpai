import discord
from discord.ext import commands
import logging
import json
from typing import List, Dict, Any, Tuple
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

    async def _process_users_data(self, users_data: List[Dict[str, Any]]) -> Tuple[int, int, List[str]]:
        from .user_utils import process_users_data
        return await process_users_data(self.db, users_data)

    @commands.command()
    async def loadusers(self, ctx: commands.Context):
        """Load users from a .txt or .json file attachment
        
        Usage: Reply to a message with a .txt or .json file attachment containing JSON user data with !loadusers
        The JSON should be an array of user objects with 'id', 'steamId', and 'handle' fields
        """
        try:
            # Check if this is a reply to another message
            if not ctx.message.reference:
                await ctx.send("❌ Please reply to a message with a .txt or .json file attachment containing JSON user data with this command.")
                return
            
            # Get the referenced message
            referenced_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            
            # Check for .txt or .json file attachment
            file_attachment = None
            for attachment in referenced_message.attachments:
                if attachment.filename.lower().endswith(('.txt', '.json')):
                    file_attachment = attachment
                    break
            
            if not file_attachment:
                await ctx.send("❌ The referenced message must have a .txt or .json file attachment.")
                return
            
            # Download and read the file content
            try:
                file_content = await file_attachment.read()
                file_text = file_content.decode('utf-8')
            except Exception as e:
                await ctx.send(f"❌ Error reading file: {str(e)}")
                return
            
            # Parse the JSON
            try:
                users_data = json.loads(file_text)
            except json.JSONDecodeError as e:
                await ctx.send(f"❌ Invalid JSON format in file: {str(e)}")
                return
            
            # Validate that it's a list
            if not isinstance(users_data, list):
                await ctx.send("❌ JSON should be an array of user objects.")
                return
            
            # Process the users
            processed_count, updated_count, errors = await self._process_users_data(users_data)
            
            # Send results
            embed = discord.Embed(title="User Import Results", color=discord.Color.green())
            embed.add_field(name="New Users Added", value=processed_count, inline=True)
            embed.add_field(name="Users Updated", value=updated_count, inline=True)
            embed.add_field(name="Total Processed", value=processed_count + updated_count, inline=True)
            
            if errors:
                embed.color = discord.Color.orange()
                error_text = "\n".join(errors[:5])  # Show first 5 errors
                if len(errors) > 5:
                    error_text += f"\n... and {len(errors) - 5} more errors"
                embed.add_field(name="Errors", value=f"```{error_text}```", inline=False)
            
            await ctx.send(embed=embed)
            
            # Log the operation
            log.info(f"User import completed by {ctx.author}: {processed_count} new, {updated_count} updated, {len(errors)} errors")
            
        except Exception as e:
            log.error(f"Error in loadusers command: {e}")
            await ctx.send(f"❌ Error loading users: {str(e)}")
