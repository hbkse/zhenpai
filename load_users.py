#!/usr/bin/env python3
"""
Idempotent user loading script
Loads users from users.json and creates/updates them in the database
Safe to run multiple times - will only create missing users and update existing ones
"""

import json
import os
import sys
import asyncio
import asyncpg
from typing import List, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def load_users_from_json():
    """Main function to load users from users.json"""
    
    # Read users.json file
    users_json_path = 'users.json'
    if not os.path.exists(users_json_path):
        logger.warning(f"{users_json_path} not found, skipping user loading")
        return
    
    try:
        with open(users_json_path, 'r') as f:
            users_data = json.load(f)
        logger.info(f"Loaded {len(users_data)} users from {users_json_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in users.json: {e}")
        return
    except Exception as e:
        logger.error(f"Could not read users.json: {e}")
        return
    
    if not isinstance(users_data, list):
        logger.error("users.json should contain an array of user objects")
        return
    
    import config
    
    # Connect to database
    try:
        pool = await asyncpg.create_pool(
            host=config.PGHOST,
            port=config.PGPORT,
            database=config.PGDATABASE,
            user=config.PGUSER,
            password=config.PGPASSWORD,
            min_size=1,
            max_size=5
        )
        logger.info("Connected to database")
    except Exception as e:
        logger.error(f"Could not connect to database: {e}")
        return
    
    try:
        # Process users
        logger.info(f"Processing {len(users_data)} users from users.json...")
        from cogs.users.user_utils import process_users_data
        from cogs.users.db import UsersDb
        
        users_db = UsersDb(pool)
        processed_count, updated_count, errors = await process_users_data(users_db, users_data)
        
        # Log results
        logger.info(f"User loading completed:")
        logger.info(f"  New users created: {processed_count}")
        logger.info(f"  Existing users updated: {updated_count}")
        logger.info(f"  Total processed: {processed_count + updated_count}")
        
        if errors:
            logger.warning(f"  Errors encountered: {len(errors)}")
            for error in errors[:5]:  # Log first 5 errors
                logger.warning(f"    - {error}")
            if len(errors) > 5:
                logger.warning(f"    ... and {len(errors) - 5} more errors")
        
        if processed_count > 0 or updated_count > 0:
            logger.info("User loading from JSON completed successfully")
        else:
            logger.info("No users needed to be created or updated")
        
    except Exception as e:
        logger.error(f"Error during user loading: {e}")
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(load_users_from_json())