from flask import Flask, jsonify, request
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5757, debug=False)
