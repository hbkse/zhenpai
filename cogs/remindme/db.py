from asyncpg import Pool
import logging
import datetime

log: logging.Logger = logging.getLogger(__name__)

class ReminderDb():
    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_reminders_ordered(self):
        query = """
            SELECT * FROM reminders ORDER BY remind_time ASC
        """
        return await self.pool.fetch(query)
    
    async def get_reminders_by_user(self, user_id: int):
        query = """
            SELECT * FROM reminders WHERE user_id = $1 ORDER BY remind_time ASC
        """
        return await self.pool.fetch(query, user_id)
    
    async def add_reminder(self, user_id: int, remind_time: datetime.datetime, message: str):
        query = """
            INSERT INTO reminders (user_id, remind_time, message) VALUES ($1, $2, $3)
        """
        return await self.pool.execute(query, user_id, remind_time, message)