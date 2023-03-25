from asyncpg import Pool
import datetime
import logging

log: logging.Logger = logging.getLogger(__name__)

class GoToSleepDb():
    def __init__(self, pool: Pool):
        self.pool = pool

    async def check_user_exists(self, user_id: int, guild_id: int):
        query = """
            SELECT EXISTS(SELECT 1 FROM gotosleep WHERE user_id = $1 AND guild_id = $2)
        """
        return await self.pool.fetchval(query, user_id, guild_id)

    async def add_user(self, user_id: int, guild_id: int):
        query = """
            INSERT INTO gotosleep (user_id, guild_id, active) VALUES ($1, $2, true)
        """
        return await self.pool.execute(query, user_id, guild_id)

    async def get_by_user_id(self, user_id: int, guild_id: int):
        query = """
            SELECT * FROM gotosleep WHERE user_id = $1 AND guild_id = $2
        """
        return await self.pool.fetchrow(query, user_id, guild_id)
    
    async def get_all_users_global(self):
        query = """
            SELECT * FROM gotosleep
        """
        return await self.pool.fetch(query)
    
    async def update_single_time(self, user_id: int, guild_id: int, day: str, start_time: datetime.time, end_time: datetime.time):
        query = """
            UPDATE gotosleep SET {0} = $3, {1} = $4 WHERE user_id = $1 AND guild_id = $2
        """
        query = query.format("{0}_start_time".format(day), "{0}_end_time".format(day))
        return await self.pool.execute(query, user_id, guild_id, start_time, end_time)
    
    async def update_all_times(self, user_id: int, guild_id: int, start_time: datetime.time, end_time: datetime.time):
        DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

        query = """
            UPDATE gotosleep SET {0} WHERE user_id = $1 AND guild_id = $2
        """
        query = query.format(', '.join(f'{day}_start_time = $3, {day}_end_time = $4' for day in DAYS))
        return await self.pool.execute(query, user_id, guild_id, start_time, end_time)
    
    async def set_user_active(self, user_id: int, guild_id: int, active: bool):
        query = """
            UPDATE gotosleep SET active = $3 WHERE user_id = $1 AND guild_id = $2
        """
        return await self.pool.execute(query, user_id, guild_id, active)