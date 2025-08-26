import aiomysql
import logging
from typing import List, Dict, Any, Optional
import config

log: logging.Logger = logging.getLogger(__name__)

class CS2MySQLDatabase:
    def __init__(self):
        self.pool: Optional[aiomysql.Pool] = None
    
    async def connect(self):
        """Initialize the MySQL connection pool for read-only access."""
        try:
            self.pool = await aiomysql.create_pool(
                host=config.MYSQL_HOST,
                port=config.MYSQL_PORT,
                user=config.MYSQL_USER,
                password=config.MYSQL_PASSWORD,
                db=config.MYSQL_DATABASE,
                autocommit=False,  # Read-only, no need for autocommit
                minsize=1,
                maxsize=5,  # Reduced pool size for read-only operations
                charset='utf8mb4',
                # read_timeout=30,
                # write_timeout=0,  # No writes needed
                # connect_timeout=10
            )
            log.info("Connected to MySQL database for CS2")
        except Exception as e:
            log.error(f"Failed to connect to MySQL database: {e}")
            raise
    
    async def close(self):
        """Close the MySQL connection pool."""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            log.info("Closed MySQL connection pool")
    
    async def get_all_tables(self) -> List[str]:
        """Get all table names from the database."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SHOW TABLES")
                tables = await cursor.fetchall()
                return [table[0] for table in tables]
    
    async def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get the schema of a specific table."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"DESCRIBE {table_name}")
                columns = await cursor.fetchall()
                return [
                    {
                        'field': col[0],
                        'type': col[1],
                        'null': col[2],
                        'key': col[3],
                        'default': col[4],
                        'extra': col[5]
                    }
                    for col in columns
                ]
    
    async def get_table_data(self, table_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get data from a specific table with optional limit."""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_table_count(self, table_name: str) -> int:
        """Get the total number of rows in a table."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                result = await cursor.fetchone()
                return result[0] if result else 0
    
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a custom query with parameters."""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                if params:
                    await cursor.execute(query, params)
                else:
                    await cursor.execute(query)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_table_data_since(self, table_name: str, timestamp_column: str, since_timestamp: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get data from a table since a specific timestamp - useful for polling/incremental updates."""
        query = f"SELECT * FROM {table_name} WHERE {timestamp_column} >= %s ORDER BY {timestamp_column} DESC LIMIT {limit}"
        return await self.execute_query(query, (since_timestamp,))

    async def get_latest_timestamp(self, table_name: str, timestamp_column: str) -> Optional[str]:
        """Get the most recent timestamp from a table - useful for tracking last poll time."""
        query = f"SELECT MAX({timestamp_column}) as latest FROM {table_name}"
        result = await self.execute_query(query)
        return result[0]['latest'] if result and result[0]['latest'] else None

    async def get_table_chunk(self, table_name: str, offset: int = 0, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get a chunk of data from a table - useful for batch processing during replication."""
        query = f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset}"
        return await self.execute_query(query)

    async def get_table_columns(self, table_name: str) -> List[str]:
        """Get just the column names for a table - useful for schema replication."""
        schema = await self.get_table_schema(table_name)
        return [col['field'] for col in schema]
