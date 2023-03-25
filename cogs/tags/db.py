from asyncpg import Pool
import logging

log: logging.Logger = logging.getLogger(__name__)

class TagsDb():
    def __init__(self, pool: Pool):
        self.pool = pool
    
    async def get_tag_by_guild(self, tag_name: str, guild_id: int):
        query = """
            SELECT * FROM tags WHERE tag = $1 AND guild_id = $2
        """
        return await self.pool.fetchrow(query, tag_name, guild_id)
    
    async def get_all_tags_in_guild(self, guild_id: int):
        query = """
            SELECT * FROM tags WHERE guild_id = $1
        """
        return await self.pool.fetch(query, guild_id)
    
    async def create_tag(self, tag_name: str, content: str, guild_id: int, user_id: int):
        query = """
            INSERT INTO tags (tag, content, guild_id, user_id) VALUES ($1, $2, $3, $4)
        """
        return await self.pool.execute(query, tag_name, content, guild_id, user_id)
    
    async def update_tag(self, tag_name: str, content: str, guild_id: int, user_id: int):
        query = """
            UPDATE tags SET content = $2, user_id = $4 WHERE tag = $1 AND guild_id = $3
        """
        return await self.pool.execute(query, tag_name, content, guild_id, user_id)