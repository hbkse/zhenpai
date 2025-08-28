import aiomysql
import logging
from typing import List, Dict, Any, Optional, Tuple
import config
from asyncpg import Pool

log: logging.Logger = logging.getLogger(__name__)

class CS2MySQLDb:
    """DB Connection for MySQL Matchzy stats"""

    MATCHZY_STATS_MAPS = "matchzy_stats_maps"
    MATCHZY_STATS_MATCHES = "matchzy_stats_matches"
    MATCHZY_STATS_PLAYERS = "matchzy_stats_players"

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
                charset='utf8mb4'
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

    async def get_matches_greater_than_matchid(self, matchid: int) -> List[Dict[str, Any]]:
        """Get all matches greater than a specific matchid."""
        query = f"SELECT * FROM {self.MATCHZY_STATS_MATCHES} WHERE matchid > {matchid}"
        return await self.execute_query(query)

    async def get_player_stats_for_match(self, matchid: int) -> List[Dict[str, Any]]:
        """Get all player stats for a specific matchid."""
        query = f"SELECT * FROM {self.MATCHZY_STATS_PLAYERS} WHERE matchid = {matchid}"
        return await self.execute_query(query)

    async def get_map_stats_for_match(self, matchid: int) -> Dict[str, Any]:
        """Get all maps for a specific matchid."""
        query = f"SELECT * FROM {self.MATCHZY_STATS_MAPS} WHERE matchid = {matchid}"
        res = await self.execute_query(query)

        # sometimes match exists but not map
        if len(res) == 1:
            return res[0]
        else: 
            return None

    async def execute_query(self, query: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        """Execute a query and return the results."""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchall()

class CS2PostgresDb:
    """DB layer for zhenpai CS2 data"""

    CS2_MATCHES = "cs2_matches"
    CS2_PLAYER_STATS = "cs2_player_stats"

    def __init__(self, pool: Pool):
        self.pool = pool
    
    async def get_last_processed_match_id(self) -> Optional[int]:
        """Get the highest matchid from our PostgreSQL table."""
        query = f"SELECT MAX(matchid) as last_match FROM {self.CS2_MATCHES}"
        result = await self.pool.fetchrow(query)
        return result['last_match'] if result and result['last_match'] else 0

    async def insert_match(self, match_data: Dict[str, Any]) -> None:
        """Insert a match into the cs2_matches table."""
        query = f"""
            INSERT INTO {self.CS2_MATCHES} (
                matchid, start_time, end_time, winner, mapname,
                team1_score, team2_score, team1_name, team2_name
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (matchid) DO NOTHING
        """
        await self.pool.execute(
            query,
            match_data['matchid'],
            match_data['start_time'],
            match_data['end_time'],
            match_data['winner'],
            match_data['mapname'],
            match_data['team1_score'],
            match_data['team2_score'],
            match_data['team1_name'],
            match_data['team2_name']
        )
    
    async def insert_player_data(self, player_data: Dict[str, Any]) -> None:
        """Insert player data into the cs2_player_stats table."""
        query = f"""
            INSERT INTO {self.CS2_PLAYER_STATS} (
                matchid, steamid64, team_name, name, kills, deaths, damage, assists,
                enemy5ks, enemy4ks, enemy3ks, enemy2ks, utility_count, utility_damage,
                utility_successes, utility_enemies, flash_count, flash_successes,
                health_points_removed_total, health_points_dealt_total, shots_fired_total,
                shots_on_target_total, v1_count, v1_wins, v2_count, v2_wins,
                entry_count, entry_wins, equipment_value, money_saved, kill_reward,
                live_time, head_shot_kills, cash_earned, enemies_flashed
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                     $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28,
                     $29, $30, $31, $32, $33, $34, $35)
        """
        await self.pool.execute(
            query,
            player_data['matchid'],
            player_data['steamid64'],
            player_data['team'],  # This will be mapped to team_name column
            player_data['name'],
            player_data['kills'],
            player_data['deaths'],
            player_data['damage'],
            player_data['assists'],
            player_data['enemy5ks'],
            player_data['enemy4ks'],
            player_data['enemy3ks'],
            player_data['enemy2ks'],
            player_data['utility_count'],
            player_data['utility_damage'],
            player_data['utility_successes'],
            player_data['utility_enemies'],
            player_data['flash_count'],
            player_data['flash_successes'],
            player_data['health_points_removed_total'],
            player_data['health_points_dealt_total'],
            player_data['shots_fired_total'],
            player_data['shots_on_target_total'],
            player_data['v1_count'],
            player_data['v1_wins'],
            player_data['v2_count'],
            player_data['v2_wins'],
            player_data['entry_count'],
            player_data['entry_wins'],
            player_data['equipment_value'],
            player_data['money_saved'],
            player_data['kill_reward'],
            player_data['live_time'],
            player_data['head_shot_kills'],
            player_data['cash_earned'],
            player_data['enemies_flashed']
        )
    
    async def get_recent_matches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent matches from our database."""
        query = f"""
            SELECT * FROM {self.CS2_MATCHES}  
            ORDER BY created_at DESC 
            LIMIT $1
        """
        rows = await self.pool.fetch(query, limit)
        return [dict(row) for row in rows]
    
    async def get_match_players(self, match_id: int) -> List[Dict[str, Any]]:
        """Get all player data for a specific match."""
        query = f"""
            SELECT * FROM {self.CS2_PLAYER_STATS} 
            WHERE matchid = $1 
            ORDER BY kills DESC
        """
        rows = await self.pool.fetch(query, match_id)
        return [dict(row) for row in rows]