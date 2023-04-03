from asyncpg import Pool
import logging
import datetime
from discord.ext import commands

log: logging.Logger = logging.getLogger(__name__)

class ReminderDb():
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_reminders_ordered(self, limit=10):
        query = """
            SELECT * FROM remindme ORDER BY remind_time ASC LIMIT $1
        """
        return await self.pool.fetch(query, limit)
    
    async def get_reminders_by_user(self, user_id: int):
        query = """
            SELECT * FROM remindme WHERE user_id = $1 ORDER BY remind_time ASC
        """
        return await self.pool.fetch(query, user_id)
    
    async def add_reminder(self, ctx: commands.Context, remind_time: datetime.datetime, content: str):
        query = """
            INSERT INTO remindme (user_id, guild_id, channel_id, remind_time, content) VALUES ($1, $2, $3, $4, $5)
        """
        return await self.pool.execute(query, ctx.author.id, ctx.guild.id, ctx.channel.id, remind_time, content)
    
    async def delete_reminder(self, reminder_id: int):
        query = """
            DELETE FROM remindme WHERE id = $1
        """
        return await self.pool.execute(query, reminder_id)