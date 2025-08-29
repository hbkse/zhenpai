"""
Shared utilities for user processing
Contains common logic for creating/updating users from data
"""

import asyncpg
from typing import List, Dict, Any, Union
import logging

logger = logging.getLogger(__name__)

async def process_users_data(
    db_interface: Union[asyncpg.Pool, 'UsersDb'], 
    users_data: List[Dict[str, Any]]
) -> tuple[int, int, List[str]]:
    """Process a list of user data and create/update users in the database
    
    Args:
        db_interface: Either an asyncpg.Pool for direct DB access or a UsersDb instance
        users_data: List of user dictionaries with 'id', 'handle', and 'steamId' fields
        
    Returns:
        Tuple of (new_users_count, updated_users_count, errors_list)
    """
    processed_count = 0
    updated_count = 0
    errors = []
    
    # Determine if we're using a pool or UsersDb
    is_pool = isinstance(db_interface, asyncpg.Pool)
    
    if is_pool:
        # Direct database access
        async with db_interface.acquire() as conn:
            return await _process_with_connection(conn, users_data)
    else:
        # Using UsersDb interface
        return await _process_with_users_db(db_interface, users_data)

async def _process_with_connection(
    conn: asyncpg.Connection, 
    users_data: List[Dict[str, Any]]
) -> tuple[int, int, List[str]]:
    """Process users using direct database connection"""
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
            existing_user = await conn.fetchrow(
                "SELECT * FROM users WHERE discord_id = $1", discord_id
            )
            
            if existing_user:
                # Check if update is needed (only update if data has changed)
                needs_update = (
                    existing_user['discord_username'] != handle or
                    existing_user['steamid64'] != steamid64
                )
                
                if needs_update:
                    await conn.execute(
                        """UPDATE users 
                           SET discord_username = $2, steamid64 = $3, updated_at = CURRENT_TIMESTAMP
                           WHERE discord_id = $1""",
                        discord_id, handle, steamid64
                    )
                    updated_count += 1
                    logger.info(f"Updated user: {handle} (ID: {discord_id})")
                else:
                    logger.debug(f"User {handle} (ID: {discord_id}) is already up to date")
            else:
                # Create new user
                await conn.execute(
                    """INSERT INTO users (discord_id, discord_username, steamid64, created_at, updated_at)
                       VALUES ($1, $2, $3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                    discord_id, handle, steamid64
                )
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

async def _process_with_users_db(
    users_db: 'UsersDb', 
    users_data: List[Dict[str, Any]]
) -> tuple[int, int, List[str]]:
    """Process users using UsersDb interface"""
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