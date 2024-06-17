from typing import List
from asyncpg import Pool
from dataclasses import dataclass
import logging
from datetime import datetime
from discord.ext import commands

log: logging.Logger = logging.getLogger(__name__)

@dataclass
class Reminder:
    """ Dataclass for a reminder. """
    id: int
    user_id: int
    guild_id: int
    channel_id: int
    remind_time: datetime
    content: str
    created_on: datetime
    is_private: bool
    sent_on: datetime
    deleted_on: datetime

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            guild_id=row['guild_id'],
            channel_id=row['channel_id'],
            remind_time=row['remind_time'],
            content=row['content'],
            created_on=row['created_on'],
            is_private=row['is_private'],
            sent_on=row['sent_on'],
            deleted_on=row['deleted_on']
        )


class ReminderDb():
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_active_reminders(self, limit=5) -> List[Reminder]:
        query = """
            SELECT * FROM remindme WHERE remind_time <= NOW() AND deleted_on IS NULL AND sent_on IS NULL ORDER BY remind_time ASC LIMIT $1;
        """
        rows = await self.pool.fetch(query, limit)
        return [Reminder.from_row(row) for row in rows]
    
    async def get_unsent_reminders_by_user(self, user_id: int) -> List[Reminder]:
        query = """
            SELECT * FROM remindme WHERE user_id = $1 AND deleted_on IS NULL AND sent_on ORDER BY remind_time ASC
        """
        rows = await self.pool.fetch(query, user_id)
        return [Reminder.from_row(row) for row in rows]
    
    async def mark_reminder_sent(self, reminder_id: int) -> bool:
        """ Mark a reminder as sent.
        
        Returns:
            True if the reminder was successfully marked as sent, False otherwise.
        """

        query = """
            UPDATE remindme SET sent_on = NOW() WHERE id = $1
        """
        result = await self.pool.execute(query, reminder_id)
        return result == "UPDATE 1"
    
    async def add_reminder(self, ctx: commands.Context, remind_time: datetime, content: str, is_private: bool) -> bool:
        """Add a reminder to the database.
        
        Args:
            ctx: The discord context of the command.
            remind_time: The point in time to remind the user.
            content: The content of the reminder.
            is_private: Whether the reminder should be sent as a DM.
            
        Returns:
            True if the reminder was successfully marked as sent, False otherwise.
        """

        query = """
            INSERT INTO remindme (user_id, guild_id, channel_id, remind_time, content, is_private) VALUES ($1, $2, $3, $4, $5, $6)
        """
        result = await self.pool.execute(query, ctx.author.id, ctx.guild.id, ctx.channel.id, remind_time, content, is_private)
        return result == "INSERT 1"
    
    async def delete_reminder(self, reminder_id: int) -> bool:
        """Delete a reminder from the database.

        Returns:
            True if the reminder was successfully deleted, False otherwise.
        """

        query = """
            UPDATE remindme SET deleted_on = NOW() WHERE id = $1
        """
        result = await self.pool.execute(query, reminder_id)
        return result == "UPDATE 1"