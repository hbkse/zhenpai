from asyncpg import Pool
import logging
from typing import Optional

log: logging.Logger = logging.getLogger(__name__)

class VoiceLoggingDb:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def set_log_channel(self, guild_id: int, channel_id: int):
        """Set the voice log channel for a guild"""
        query = """
        INSERT INTO voice_log_config (guild_id, log_channel_id, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (guild_id) 
        DO UPDATE SET 
            log_channel_id = $2,
            updated_at = NOW()
        """
        await self.pool.execute(query, guild_id, channel_id)

    async def get_log_channel(self, guild_id: int) -> Optional[int]:
        """Get the voice log channel for a guild"""
        query = """
        SELECT log_channel_id FROM voice_log_config 
        WHERE guild_id = $1 AND enabled = true
        """
        result = await self.pool.fetchval(query, guild_id)
        return result

    async def disable_logging(self, guild_id: int):
        """Disable voice logging for a guild"""
        query = """
        UPDATE voice_log_config 
        SET enabled = false, updated_at = NOW()
        WHERE guild_id = $1
        """
        await self.pool.execute(query, guild_id)

    async def enable_logging(self, guild_id: int):
        """Enable voice logging for a guild"""
        query = """
        UPDATE voice_log_config 
        SET enabled = true, updated_at = NOW()
        WHERE guild_id = $1
        """
        await self.pool.execute(query, guild_id)