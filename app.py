from flask import Flask, jsonify, request
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

log: logging.Logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_sync_db_connection():
    import start # avoiding circular import
    conn_opts = start.db_connection_options()
    del conn_opts['min_size']
    del conn_opts['max_size']
    return psycopg2.connect(**conn_opts, cursor_factory=RealDictCursor)

@app.route('/')
def hello_world():
    """Basic hello world endpoint that returns empty JSON."""
    log.info("Hello world endpoint accessed")
    return jsonify({})

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})

@app.route('/guelo_start', methods=['POST'])
def guelo_start():
    try:
        data = request.get_json() or {}
        image_url = data.get('image_url')
        
        log.info(f"Received /guelo_start request with image_url: {image_url}, contacting internal server")
        
        payload = {}
        if image_url:
            payload['image_url'] = image_url
            
        response = requests.post(
            'http://127.0.0.1:8081/start-live-tracking',
            json=payload if payload else None,
            timeout=5
        )
        return '', response.status_code
    except requests.exceptions.RequestException as e:
        log.info(f"Error contacting internal server: {e}")
        return '', 500

@app.route('/match_history')
def get_cs2_matches():
    """Get CS2 matches with pagination
    
    Query parameters:
    - page: Page number (default: 1)
    - limit: Number of matches per page (default: 10, max: 50)
    - offset: Alternative to page, direct offset (optional)
    """
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', type=int)
        
        # Validate parameters
        if page < 1:
            return jsonify({"error": "Page must be 1 or greater"}), 400
        if limit < 1 or limit > 50:
            return jsonify({"error": "Limit must be between 1 and 50"}), 400
        if offset is None:
            offset = (page - 1) * limit
        if offset < 0:
            return jsonify({"error": "Offset must be 0 or greater"}), 400
        
        with get_sync_db_connection() as conn:
            with conn.cursor() as cur:
                # Query the matches table with pagination
                matches_query = """
                    SELECT * FROM cs2_matches 
                    ORDER BY start_time DESC 
                    LIMIT %s OFFSET %s
                """
                cur.execute(matches_query, (limit, offset))
                matches = cur.fetchall()
                
                # Convert matches to list of dictionaries
                matches_list = []
                for match in matches:
                    match_dict = dict(match)
                    matchid = match_dict['matchid']
                    
                    # Query player stats for this match
                    stats_query = """
                        SELECT * FROM cs2_player_stats 
                        WHERE matchid = %s
                        ORDER BY damage DESC
                    """
                    cur.execute(stats_query, (matchid,))
                    player_stats = cur.fetchall()

                    # Add player_stats as a list to the match
                    match_dict['player_stats'] = [dict(stat) for stat in player_stats]
                    matches_list.append(match_dict)
                
                # Get total count for pagination metadata
                count_query = "SELECT COUNT(*) as total FROM cs2_matches"
                cur.execute(count_query)
                total_matches = cur.fetchone()['total']
                
                result = {
                    "matches": matches_list,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "offset": offset,
                        "total": total_matches,
                        "total_pages": (total_matches + limit - 1) // limit
                    }
                }
        
        log.info(f"match_history endpoint accessed - page: {page}, limit: {limit}, offset: {offset}")
        return jsonify(result)
        
    except Exception as e:
        log.error(f"Error in match_history endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/user_points')
def get_user_points():
    """Get user's current points and transaction history
    
    Query parameters:
    - discord_id: Discord user ID (required)
    - history_limit: Number of history transactions to return (optional, returns all if not specified)
    """
    try:
        discord_id = request.args.get('discord_id', type=int)
        history_limit = request.args.get('history_limit', type=int)
        
        # Validate parameters
        if not discord_id:
            return jsonify({"error": "discord_id parameter is required"}), 400
        if history_limit is not None and history_limit < 1:
            return jsonify({"error": "history_limit must be 1 or greater"}), 400
        
        with get_sync_db_connection() as conn:
            with conn.cursor() as cur:
                # Get current total points (reusing PointsDb query)
                points_query = """
                    SELECT COALESCE(SUM(change_value), 0) as total_points
                    FROM points
                    WHERE discord_id = %s
                """
                cur.execute(points_query, (discord_id,))
                total_points_result = cur.fetchone()
                total_points = total_points_result['total_points'] if total_points_result else 0
                
                # Get recent transactions with running balance calculation
                history_query = """
                    SELECT 
                        change_value,
                        created_at,
                        category,
                        reason,
                        SUM(change_value) OVER (
                            ORDER BY created_at ASC, id ASC 
                            ROWS UNBOUNDED PRECEDING
                        ) as running_balance
                    FROM points
                    WHERE discord_id = %s
                    ORDER BY created_at DESC
                """ + (f" LIMIT {history_limit}" if history_limit is not None else "")
                
                cur.execute(history_query, (discord_id,))
                history_results = cur.fetchall()
                
                # Convert history to list of dictionaries
                history = []
                for transaction in history_results:
                    transaction_dict = dict(transaction)
                    # Convert datetime to ISO string for JSON serialization
                    if transaction_dict['created_at']:
                        transaction_dict['created_at'] = transaction_dict['created_at'].isoformat()
                    history.append(transaction_dict)
                
                # Get user info if available
                user_query = """
                    SELECT discord_username, steamid64
                    FROM users
                    WHERE discord_id = %s
                """
                cur.execute(user_query, (discord_id,))
                user_result = cur.fetchone()
                user_info = dict(user_result) if user_result else None
                
                result = {
                    "discord_id": discord_id,
                    "user_info": user_info,
                    "current_points": total_points,
                    "points_history": history,
                    "history_metadata": {
                        "limit": history_limit,
                        "returned_count": len(history)
                    }
                }
        
        log.info(f"user_points endpoint accessed - discord_id: {discord_id}, history_limit: {history_limit}")
        return jsonify(result)
        
    except Exception as e:
        log.error(f"Error in user_points endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5757, debug=False)
