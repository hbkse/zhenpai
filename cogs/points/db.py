from asyncpg import Pool
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

log: logging.Logger = logging.getLogger(__name__)

class PointsDb:
    # table names
    POINTS = 'points'
    POINT_BALANCE = 'point_balances'
    PROCESSED_EVENTS = 'processed_events'
    CS2_MATCHES = 'cs2_matches'
    CS2_PLAYER_STATS = 'cs2_player_stats'

    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_points_leaderboard(self, limit: int = 10):
        """
        Get the top users by total points
        """
        query = """
        SELECT 
            discord_id,
            SUM(change_value) as total_points
        FROM points
        GROUP BY discord_id
        ORDER BY total_points DESC
        LIMIT $1
        """
        return await self.pool.fetch(query, limit)

    async def get_recent_points_transactions_by_discord_id(self, id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent points transactions for a discord user
        """
        query = """
        SELECT 
            change_value,
            created_at,
            category,
            reason
        FROM points
        WHERE discord_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """
        return await self.pool.fetch(query, id, limit)

    async def get_total_points_by_discord_id(self, id: int):
        """
        Get current total points for a discord user
        """
        query = """
        SELECT COALESCE(SUM(change_value), 0) as total_points
        FROM points
        WHERE discord_id = $1
        """
        return await self.pool.fetchval(query, id)

    async def add_points_reward(self, discord_id: int, change_value: int, reason: str):
        """
        Add a manual points reward for a user
        """
        query = """
        INSERT INTO points (discord_id, change_value, created_at, category, reason, event_source, event_source_id)
        VALUES ($1, $2, NOW(), $3, $4, $5, $6)
        """
        await self.pool.execute(query, discord_id, change_value, "Admin Reward", reason, None, None)

    async def perform_cs2_event_transaction(self, rows: List[Tuple[Any, ...]], matchid: int):
        """inserts all point records and updates processed_events table in a single transaction"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # Insert point records in batch
                    if rows:
                        await conn.executemany(
                            """
                            INSERT INTO points (discord_id, change_value, created_at, category, reason, event_source, event_source_id)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                            """,
                            rows
                        )
                    # Update processed_events table to mark as processed
                    if matchid:
                        await conn.execute(
                            """
                            INSERT INTO processed_events (event_source, event_source_id)
                            VALUES ($1, $2)
                            """,
                            'cs2_matches', matchid
                        )
                    return len(rows)
                except Exception as e:
                    # Transaction will automatically rollback due to context manager
                    raise Exception(f"Failed to process CS2 events: {str(e)}")

    async def get_match_players(self, match_id: int) -> List[Dict[str, Any]]:
        """Get all player data for a specific match."""
        query = f"""
            SELECT * FROM {self.CS2_PLAYER_STATS} 
            WHERE matchid = $1 
            ORDER BY kills DESC
        """
        rows = await self.pool.fetch(query, match_id)
        return [dict(row) for row in rows]

    async def fetch_unprocessed_cs2_matches(self):
        return await self._fetch_unprocessed(self.CS2_MATCHES, "matchid")

    async def _fetch_unprocessed(self, table_source: str, source_id_column: str):
        """
        Helper that fetches unprocessed rows from the specified table based on processed_events table
        """
        query = f"""
        SELECT t.*
        FROM {table_source} t
        WHERE NOT EXISTS (
            SELECT 1
            FROM processed_events p
            WHERE p.event_source = '{table_source}' AND p.event_source_id = t.{source_id_column}
        )
        """
        return await self.pool.fetch(query)