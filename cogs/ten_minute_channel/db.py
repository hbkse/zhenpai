from typing import List
from asyncpg import Pool
from dataclasses import dataclass
import logging

log: logging.Logger = logging.getLogger(__name__)


@dataclass
class TenMinuteChannelRecord:
    """Dataclass for a 10-minute channel."""
    id: int
    guild_id: int
    channel_id: int
    delete_after_minutes: int
    created_at: str

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row['id'],
            guild_id=row['guild_id'],
            channel_id=row['channel_id'],
            delete_after_minutes=row['delete_after_minutes'],
            created_at=row['created_at']
        )


class TenMinuteChannelDb:
    def __init__(self, pool: Pool):
        self.pool = pool

    async def add_channel(self, guild_id: int, channel_id: int, delete_after_minutes: int = 10) -> bool:
        """Add a channel to the 10-minute deletion list.

        Args:
            guild_id: The guild ID
            channel_id: The channel ID
            delete_after_minutes: Number of minutes after which to delete messages (default: 10)

        Returns:
            True if the channel was successfully added, False if it already existed.
        """
        query = """
            INSERT INTO ten_minute_channels (guild_id, channel_id, delete_after_minutes)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, channel_id) DO NOTHING
        """
        result = await self.pool.execute(query, guild_id, channel_id, delete_after_minutes)
        return result == "INSERT 0 1"

    async def remove_channel(self, guild_id: int, channel_id: int) -> bool:
        """Remove a channel from the 10-minute deletion list.

        Returns:
            True if the channel was successfully removed, False otherwise.
        """
        query = """
            DELETE FROM ten_minute_channels
            WHERE guild_id = $1 AND channel_id = $2
        """
        result = await self.pool.execute(query, guild_id, channel_id)
        return result == "DELETE 1"

    async def get_all_channels(self) -> List[TenMinuteChannelRecord]:
        """Get all channels that should have 10-minute message deletion."""
        query = """
            SELECT * FROM ten_minute_channels
        """
        rows = await self.pool.fetch(query)
        return [TenMinuteChannelRecord.from_row(row) for row in rows]

    async def get_channels_for_guild(self, guild_id: int) -> List[TenMinuteChannelRecord]:
        """Get all 10-minute channels for a specific guild."""
        query = """
            SELECT * FROM ten_minute_channels
            WHERE guild_id = $1
        """
        rows = await self.pool.fetch(query, guild_id)
        return [TenMinuteChannelRecord.from_row(row) for row in rows]

    async def is_channel_registered(self, guild_id: int, channel_id: int) -> bool:
        """Check if a channel is registered for 10-minute deletion."""
        query = """
            SELECT EXISTS(
                SELECT 1 FROM ten_minute_channels
                WHERE guild_id = $1 AND channel_id = $2
            )
        """
        return await self.pool.fetchval(query, guild_id, channel_id)

    async def update_delete_after_minutes(self, guild_id: int, channel_id: int, delete_after_minutes: int) -> bool:
        """Update the deletion period for a channel.

        Args:
            guild_id: The guild ID
            channel_id: The channel ID
            delete_after_minutes: New number of minutes after which to delete messages

        Returns:
            True if the channel was successfully updated, False otherwise.
        """
        query = """
            UPDATE ten_minute_channels
            SET delete_after_minutes = $3
            WHERE guild_id = $1 AND channel_id = $2
        """
        result = await self.pool.execute(query, guild_id, channel_id, delete_after_minutes)
        return result == "UPDATE 1"

    async def get_channel(self, guild_id: int, channel_id: int) -> TenMinuteChannelRecord:
        """Get a specific channel record.

        Args:
            guild_id: The guild ID
            channel_id: The channel ID

        Returns:
            TenMinuteChannelRecord or None if not found
        """
        query = """
            SELECT * FROM ten_minute_channels
            WHERE guild_id = $1 AND channel_id = $2
        """
        row = await self.pool.fetchrow(query, guild_id, channel_id)
        return TenMinuteChannelRecord.from_row(row) if row else None
