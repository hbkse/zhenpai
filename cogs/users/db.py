from asyncpg import Pool
import logging

log: logging.Logger = logging.getLogger(__name__)

class UsersDb():
    def __init__(self, pool: Pool):
        self.pool = pool
    
    async def get_user_by_discord_id(self, discord_id: int):
        """Get user by Discord ID"""
        query = """
            SELECT * FROM users WHERE discord_id = $1
        """
        return await self.pool.fetchrow(query, discord_id)
    
    async def get_user_by_steamid64(self, steamid64: int):
        """Get user by Steam ID"""
        query = """
            SELECT * FROM users WHERE steamid64 = $1
        """
        return await self.pool.fetchrow(query, steamid64)
    
    async def get_all_users(self):
        """Get all users"""
        query = """
            SELECT * FROM users ORDER BY discord_id
        """
        return await self.pool.fetch(query)
    
    async def create_user(self, discord_id: int, discord_username: str, steamid64: int = None):
        """Create a new user"""
        query = """
            INSERT INTO users (discord_id, discord_username, steamid64) 
            VALUES ($1, $2, $3)
            ON CONFLICT (discord_id) DO UPDATE SET 
                discord_username = EXCLUDED.discord_username,
                steamid64 = EXCLUDED.steamid64
            RETURNING *
        """
        return await self.pool.fetchrow(query, discord_id, discord_username, steamid64)
    
    async def update_user_steamid64(self, discord_id: int, steamid64: int):
        """Update user's Steam ID"""
        query = """
            UPDATE users SET steamid64 = $2 WHERE discord_id = $1
            RETURNING *
        """
        return await self.pool.fetchrow(query, discord_id, steamid64)
    
    async def delete_user(self, discord_id: int):
        """Delete a user"""
        query = """
            DELETE FROM users WHERE discord_id = $1
        """
        return await self.pool.execute(query, discord_id)
