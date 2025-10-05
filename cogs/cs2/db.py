import aiomysql
import logging
from typing import List, Dict, Any, Optional, Tuple
import config
from asyncpg import Pool, Connection

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
                autocommit=True,  # if you don't commit after read, conn won't update to next consistent version
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
    
    async def get_latest_match_id(self) -> int:
        """Get the latest match ID from the matches table."""
        query = f"SELECT MAX(matchid) as latest_id FROM {self.MATCHZY_STATS_MATCHES}"
        result = await self.execute_query(query)
        return result[0]['latest_id'] if result and result[0]['latest_id'] else 0
    
    async def get_match_by_id(self, matchid: int) -> Optional[Dict[str, Any]]:
        """Get match data by specific matchid."""
        query = f"SELECT * FROM {self.MATCHZY_STATS_MATCHES} WHERE matchid = %s"
        result = await self.execute_query(query, (matchid,))
        return result[0] if result else None

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

    async def process_matchzy_data_transaction(
        self, 
        match_data: Dict[str, Any], 
        players_data: List[Dict[str, Any]]
    ) -> None:
        """
        Insert a match and all associated player data in a single transaction
        
        Args:
            match_data: Dictionary containing match information
            players_data: List of dictionaries containing player statistics
        
        Raises:
            Exception: If the transaction fails, all operations are rolled back
        """
        async with self.pool.acquire() as conn:
            conn: Connection
            async with conn.transaction():
                match_query = f"""
                    INSERT INTO {self.CS2_MATCHES} (
                        matchid, start_time, end_time, winner, mapname,
                        team1_score, team2_score, team1_name, team2_name
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (matchid) DO NOTHING
                """
                
                await conn.execute(
                    match_query,
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
                
                # Prepare player data as list of tuples for executemany
                player_values = [
                    (
                        player_data['matchid'],
                        player_data['steamid64'],
                        player_data['team'],
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
                    for player_data in players_data
                ]
                
                player_query = f"""
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
                
                # Batch insert all player data
                await conn.executemany(player_query, player_values)
    
    async def get_recent_matches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent matches from our database."""
        query = f"""
            SELECT * FROM {self.CS2_MATCHES}  
            ORDER BY start_time DESC 
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

    async def get_player_winrates(self, all_time: bool = False) -> List[Dict[str, Any]]:
        """Calculate win/loss records for all players, grouped by steamid64.

        Args:
            all_time: If True, query all matches. If False, only query current month's matches.
        """
        date_filter = "" if all_time else "WHERE m.start_time >= DATE_TRUNC('month', CURRENT_TIMESTAMP) + INTERVAL '12 hours'"

        query = f"""
            WITH player_matches AS (
                SELECT
                    ps.steamid64,
                    ps.team_name,
                    m.winner,
                    CASE
                        WHEN ps.team_name = m.winner THEN 1
                        ELSE 0
                    END as is_win
                FROM {self.CS2_PLAYER_STATS} ps
                JOIN {self.CS2_MATCHES} m ON ps.matchid = m.matchid
                {date_filter}
            ),
            player_stats AS (
                SELECT
                    steamid64,
                    SUM(is_win) as wins,
                    COUNT(*) - SUM(is_win) as losses,
                    COUNT(*) as total_matches,
                    ROUND(
                        CASE
                            WHEN COUNT(*) > 0 THEN (SUM(is_win)::DECIMAL / COUNT(*)) * 100
                            ELSE 0
                        END,
                        1
                    ) as winrate
                FROM player_matches
                GROUP BY steamid64
                HAVING COUNT(*) > 0
            )
            SELECT
                ps.steamid64,
                ps.wins,
                ps.losses,
                ps.total_matches,
                ps.winrate,
                COALESCE(u.discord_username, 'Unknown Player') as display_name,
                u.discord_id
            FROM player_stats ps
            LEFT JOIN users u ON ps.steamid64 = u.steamid64
            ORDER BY ps.winrate DESC, ps.wins DESC
        """
        rows = await self.pool.fetch(query)
        return [dict(row) for row in rows]

    async def get_comprehensive_player_stats(self, all_time: bool = False) -> List[Dict[str, Any]]:
        """Get comprehensive statistics for all players, grouped by steamid64.

        Args:
            all_time: If True, query all matches. If False, only query current month's matches.
        """
        date_filter = "" if all_time else "WHERE m.start_time >= DATE_TRUNC('month', CURRENT_TIMESTAMP) + INTERVAL '12 hours'"

        query = f"""
            WITH player_matches AS (
                SELECT
                    ps.steamid64,
                    ps.team_name,
                    m.winner,
                    ps.kills,
                    ps.deaths,
                    ps.assists,
                    ps.damage,
                    m.team1_score,
                    m.team2_score,
                    ps.head_shot_kills,
                    ps.v1_count,
                    ps.v1_wins,
                    ps.entry_count,
                    ps.entry_wins,
                    ps.utility_damage,
                    ps.flash_successes,
                    ps.flash_count,
                    CASE
                        WHEN ps.team_name = m.winner THEN 1
                        ELSE 0
                    END as is_win,
                    (m.team1_score + m.team2_score) as total_rounds
                FROM {self.CS2_PLAYER_STATS} ps
                JOIN {self.CS2_MATCHES} m ON ps.matchid = m.matchid
                {date_filter}
            ),
            player_stats AS (
                SELECT
                    steamid64,
                    COUNT(*) as matches_played,
                    SUM(is_win) as wins,
                    COUNT(*) - SUM(is_win) as losses,
                    ROUND(
                        CASE
                            WHEN COUNT(*) > 0 THEN (SUM(is_win)::DECIMAL / COUNT(*)) * 100
                            ELSE 0
                        END,
                        1
                    ) as winrate,
                    ROUND(SUM(kills)::DECIMAL / NULLIF(COUNT(*), 0), 1) as avg_kills,
                    ROUND(SUM(deaths)::DECIMAL / NULLIF(COUNT(*), 0), 1) as avg_deaths,
                    ROUND(SUM(assists)::DECIMAL / NULLIF(COUNT(*), 0), 1) as avg_assists,
                    ROUND(
                        CASE
                            WHEN SUM(deaths) > 0 THEN (SUM(kills) + SUM(assists))::DECIMAL / SUM(deaths)
                            ELSE SUM(kills) + SUM(assists)
                        END,
                        2
                    ) as kda_ratio,
                    ROUND(
                        CASE
                            WHEN SUM(deaths) > 0 THEN SUM(kills)::DECIMAL / SUM(deaths)
                            ELSE SUM(kills)
                        END,
                        2
                    ) as kd_ratio,
                    ROUND(SUM(damage)::DECIMAL / NULLIF(SUM(total_rounds), 0), 1) as avg_damage_per_round,
                    ROUND(
                        CASE
                            WHEN SUM(kills) > 0 THEN (SUM(head_shot_kills)::DECIMAL / SUM(kills)) * 100
                            ELSE 0
                        END,
                        1
                    ) as headshot_percentage,
                    ROUND(
                        CASE
                            WHEN SUM(v1_count) > 0 THEN (SUM(v1_wins)::DECIMAL / SUM(v1_count)) * 100
                            ELSE 0
                        END,
                        1
                    ) as clutch_success_rate,
                    ROUND(
                        CASE
                            WHEN SUM(entry_count) > 0 THEN (SUM(entry_wins)::DECIMAL / SUM(entry_count)) * 100
                            ELSE 0
                        END,
                        1
                    ) as entry_success_rate,
                    ROUND(SUM(utility_damage)::DECIMAL / NULLIF(COUNT(*), 0), 1) as avg_utility_damage,
                    ROUND(
                        CASE
                            WHEN SUM(flash_count) > 0 THEN (SUM(flash_successes)::DECIMAL / SUM(flash_count)) * 100
                            ELSE 0
                        END,
                        1
                    ) as flash_success_rate,
                    SUM(kills) as total_kills,
                    SUM(deaths) as total_deaths,
                    SUM(assists) as total_assists,
                    SUM(damage) as total_damage
                FROM player_matches
                GROUP BY steamid64
                HAVING COUNT(*) > 0
            )
            SELECT
                ps.steamid64,
                ps.matches_played,
                ps.wins,
                ps.losses,
                ps.winrate,
                ps.avg_kills,
                ps.avg_deaths,
                ps.avg_assists,
                ps.kda_ratio,
                ps.kd_ratio,
                ps.avg_damage_per_round,
                ps.headshot_percentage,
                ps.clutch_success_rate,
                ps.entry_success_rate,
                ps.avg_utility_damage,
                ps.flash_success_rate,
                ps.total_kills,
                ps.total_deaths,
                ps.total_assists,
                ps.total_damage,
                COALESCE(u.discord_username, 'Unknown Player') as display_name,
                u.discord_id
            FROM player_stats ps
            LEFT JOIN users u ON ps.steamid64 = u.steamid64
            ORDER BY ps.avg_damage_per_round DESC, ps.kda_ratio DESC
        """
        rows = await self.pool.fetch(query)
        return [dict(row) for row in rows]

    async def calculate_team_odds(self, team1_steamids: List[int], team2_steamids: List[int]) -> Dict[str, Any]:
        """Calculate match odds based on team ADR sums, normalized by subtracting average ADR.

        Args:
            team1_steamids: List of steamid64s for team 1
            team2_steamids: List of steamid64s for team 2

        Returns:
            Dictionary containing team ADRs and odds
        """
        # Get player stats for ADR calculation - always use all-time data for odds
        all_stats = await self.get_comprehensive_player_stats(all_time=True)
        steamid_adr_map = {stats['steamid64']: float(stats['avg_damage_per_round']) for stats in all_stats}

        # Calculate average ADR across players with 5+ matches
        qualified_stats = [stats for stats in all_stats if stats['matches_played'] >= 5]
        if qualified_stats:
            average_adr = sum(float(stats['avg_damage_per_round']) for stats in qualified_stats) / len(qualified_stats)
        else:
            average_adr = 70.0  # Default if no qualified stats

        def get_player_adr(steamid64: int) -> float:
            """Get player ADR by steamid64, return default if not found."""
            return steamid_adr_map.get(steamid64, average_adr)  # Use average as default

        # Calculate team ADR sums (normalized by subtracting average)
        team1_normalized_adrs = [get_player_adr(steamid) - average_adr for steamid in team1_steamids]
        team2_normalized_adrs = [get_player_adr(steamid) - average_adr for steamid in team2_steamids]

        team1_normalized_sum = sum(team1_normalized_adrs)
        team2_normalized_sum = sum(team2_normalized_adrs)

        # Calculate raw ADR sums for display
        team1_adr = sum(get_player_adr(steamid) for steamid in team1_steamids)
        team2_adr = sum(get_player_adr(steamid) for steamid in team2_steamids)

        # Calculate odds based on normalized ADR difference
        # If both teams are exactly average, odds are 50/50
        # Otherwise, calculate based on relative performance above/below average
        if team1_normalized_sum == team2_normalized_sum:
            team1_odds = team2_odds = 50.0
        else:
            # Use normalized difference to calculate odds
            adr_difference = team1_normalized_sum - team2_normalized_sum

            # Convert difference to probability using a sigmoid-like function
            # The larger the absolute difference, the more skewed the odds
            total_abs_difference = abs(adr_difference)

            if total_abs_difference > 0:
                # Scale the difference - every 50 ADR difference = ~20% odds shift
                scaling_factor = total_abs_difference / 50.0

                if adr_difference > 0:  # team1 is better
                    team1_odds = 50.0 + min(40.0, scaling_factor * 20.0)
                    team2_odds = 100.0 - team1_odds
                else:  # team2 is better
                    team2_odds = 50.0 + min(40.0, scaling_factor * 20.0)
                    team1_odds = 100.0 - team2_odds
            else:
                team1_odds = team2_odds = 50.0

        return {
            'team1_adr': team1_adr,
            'team2_adr': team2_adr,
            'team1_odds': team1_odds,
            'team2_odds': team2_odds,
            'total_adr': team1_adr + team2_adr,
            'average_adr': average_adr,
            'team1_normalized_sum': team1_normalized_sum,
            'team2_normalized_sum': team2_normalized_sum
        }

    async def insert_match_bet(
        self,
        cs_match_id: int,
        user_id: int,
        amount: int,
        team_name: str,
        odds: float
    ) -> None:
        """
        Insert a bet into the cs2_match_bets table and subtract points from user's balance.
        This happens in a transaction so both operations succeed or fail together.
        Payout is calculated as: amount / win_probability (e.g., 1000 / 0.55 = 1818)
        """
        payout = int(amount / odds)

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Insert the bet
                bet_query = """
                    INSERT INTO cs2_match_bets (
                        cs_match_id, user_id, amount, team_name, odds, payout, active
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                """
                bet_id = await conn.fetchval(bet_query, cs_match_id, user_id, amount, team_name, odds, payout, True)

                # Insert points transaction (negative for bet placement)
                points_query = """
                    INSERT INTO points (
                        discord_id, change_value, category, reason,
                        event_source, event_source_id
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                """
                points_id = await conn.fetchval(
                    points_query,
                    user_id,
                    -amount,  # Negative because we're subtracting
                    'cs2_bet',
                    f'Placed bet on {team_name} for match {cs_match_id}',
                    'cs2_match_bets',
                    bet_id
                )

                # Update point_balances
                balance_query = """
                    INSERT INTO point_balances (discord_id, current_balance, last_transaction_id, last_updated)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (discord_id)
                    DO UPDATE SET
                        current_balance = point_balances.current_balance + $2,
                        last_transaction_id = $3,
                        last_updated = NOW()
                """
                await conn.execute(balance_query, user_id, -amount, points_id)

    async def process_cs2_match_bets(self, cs_match_id: int, winning_team: str) -> None:
        """
        Process all bets for a completed match in a single transaction.

        Args:
            cs_match_id: The match ID to process bets for
            winning_team: The name of the winning team
        """
        async with self.pool.acquire() as conn:
            conn: Connection
            async with conn.transaction():
                # Get all bets for this match
                bets_query = """
                    SELECT * FROM cs2_match_bets
                    WHERE cs_match_id = $1
                """
                bets = await conn.fetch(bets_query, cs_match_id)

                # Check for inactive bets - this shouldn't happen
                inactive_bets = [bet for bet in bets if not bet['active']]
                if inactive_bets:
                    log.warning(
                        f"Found {len(inactive_bets)} inactive bets for match {cs_match_id}. "
                        f"This indicates bets were already processed or manually deactivated."
                    )

                # Process only active bets
                active_bets = [bet for bet in bets if bet['active']]

                for bet in active_bets:
                    # Determine if this bet won
                    bet_won = bet['team_name'] == winning_team

                    # Only process winnings - losses were already deducted when bet was placed
                    if bet_won:
                        # Winner gets payout
                        points_change = bet['payout']
                        reason = f"Won CS2 Bet {cs_match_id}"

                        # Insert points record
                        points_query = """
                            INSERT INTO points (
                                discord_id, change_value, category, reason,
                                event_source, event_source_id
                            ) VALUES ($1, $2, $3, $4, $5, $6)
                            RETURNING id
                        """
                        points_id = await conn.fetchval(
                            points_query,
                            bet['user_id'],
                            points_change,
                            'cs2_bet',
                            reason,
                            'cs2_match_bets',
                            bet['id']
                        )

                        # Update point_balances
                        balance_query = """
                            UPDATE point_balances
                            SET current_balance = current_balance + $1,
                                last_transaction_id = $2,
                                last_updated = NOW()
                            WHERE discord_id = $3
                        """
                        await conn.execute(balance_query, points_change, points_id, bet['user_id'])

                    # Mark bet as inactive (both winning and losing bets)
                    update_bet_query = """
                        UPDATE cs2_match_bets
                        SET active = FALSE
                        WHERE id = $1
                    """
                    await conn.execute(update_bet_query, bet['id'])

                log.info(
                    f"Processed {len(active_bets)} bets for match {cs_match_id}. "
                    f"Winning team: {winning_team}"
                )

    async def get_user_balance(self, user_id: int) -> int:
        """Get current point balance for a specific user."""
        query = """
            SELECT current_balance
            FROM point_balances
            WHERE discord_id = $1
        """
        result = await self.pool.fetchval(query, user_id)
        return result if result is not None else 0