from asyncpg import Pool, Record
import datetime
import logging
from typing import List

log: logging.Logger = logging.getLogger(__name__)

class GoToSleepDb():
    def __init__(self, pool: Pool):
        self.pool = pool

    async def check_user_exists(self, user_id: int) -> bool:
        query = """
            SELECT EXISTS(SELECT 1 FROM gotosleep WHERE user_id = $1)
        """
        return await self.pool.fetchval(query, user_id)

    async def add_user(self, user_id: int) -> str:
        query = """
            INSERT INTO gotosleep (user_id, active) VALUES ($1, true)
        """
        return await self.pool.execute(query, user_id)

    async def get_by_user_id(self, user_id: int) -> Record:
        query = """
            SELECT * FROM gotosleep WHERE user_id = $1
        """
        return await self.pool.fetchrow(query, user_id)
    
    async def get_all_users(self) -> List[Record]:
        query = """
            SELECT * FROM gotosleep
        """
        return await self.pool.fetch(query)
    
    async def update_single_time(self, user_id: int, day: str, start_time: datetime.time, end_time: datetime.time) -> str:
        query = """
            UPDATE gotosleep SET {0} = $2, {1} = $3 WHERE user_id = $1
        """
        query = query.format("{0}_start_time".format(day), "{0}_end_time".format(day))
        return await self.pool.execute(query, user_id, start_time, end_time)
    
    async def update_all_times(self, user_id: int, start_time: datetime.time, end_time: datetime.time) -> str:
        DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

        query = """
            UPDATE gotosleep SET {0} WHERE user_id = $1
        """
        query = query.format(', '.join(f'{day}_start_time = $2, {day}_end_time = $3' for day in DAYS))
        return await self.pool.execute(query, user_id, start_time, end_time)
    
    async def set_user_active(self, user_id: int, active: bool) -> str:
        query = """
            UPDATE gotosleep SET active = $2 WHERE user_id = $1
        """
        return await self.pool.execute(query, user_id, active)