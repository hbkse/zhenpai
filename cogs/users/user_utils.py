"""
Shared utilities for user processing
Contains common logic for creating/updating users from data
"""

from typing import List, Dict, Any
import logging
from .db import UsersDb

logger = logging.getLogger(__name__)

async def process_users_data(
    users_db: UsersDb, 
    users_data: List[Dict[str, Any]]
) -> tuple[int, int, List[str]]:
    """Process a list of user data and create/update users in the database
    
    Args:
        users_db: UsersDb instance for database operations
        users_data: List of user dictionaries with 'id', 'handle', and 'steamId' fields
        
    Returns:
        Tuple of (new_users_count, updated_users_count, errors_list)
    """
    processed_count = 0
    updated_count = 0
    errors = []
    
    for user_data in users_data:
        try:
            # Extract required fields
            discord_id = int(user_data.get('id'))
            handle = user_data.get('handle')
            steam_id = user_data.get('steamId')
            
            if not discord_id or not handle:
                errors.append(f"Missing required fields for user: {user_data}")
                continue
            
            # Convert steam_id to int if present
            steamid64 = int(steam_id) if steam_id else None
            
            # Check if user already exists
            existing_user = await users_db.get_user_by_discord_id(discord_id)
            
            if existing_user:
                # Update existing user (UsersDb.create_user handles updates)
                await users_db.create_user(discord_id, handle, steamid64)
                updated_count += 1
                logger.info(f"Updated user: {handle} (ID: {discord_id})")
            else:
                # Create new user
                await users_db.create_user(discord_id, handle, steamid64)
                processed_count += 1
                logger.info(f"Created new user: {handle} (ID: {discord_id})")
                
        except (ValueError, KeyError) as e:
            error_msg = f"Invalid data for user: {user_data} - {str(e)}"
            errors.append(error_msg)
            logger.warning(error_msg)
        except Exception as e:
            error_msg = f"Error processing user {user_data}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
    
    return processed_count, updated_count, errors

