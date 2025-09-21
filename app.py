from flask import Flask, jsonify, request, send_file
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import os
from pathlib import Path
from config import CS2_DEMO_DIRECTORY

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
                # Get current total points from precomputed balances
                points_query = """
                    SELECT COALESCE(current_balance, 0) as total_points
                    FROM point_balances
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

@app.route('/upload-demo', methods=['POST'])
def upload_demo():
    """Handle demo file uploads from MatchZy CS2 plugin

    Expected headers:
    - MatchZy-FileName: Name of the demo file
    - MatchZy-MatchId: Unique ID of the match
    - MatchZy-MapNumber: Zero-indexed map number in the series

    The request body contains the zipped demo file data.
    """
    try:
        # Read MatchZy headers
        filename = request.headers.get('MatchZy-FileName')
        match_id = request.headers.get('MatchZy-MatchId')
        map_number = request.headers.get('MatchZy-MapNumber')

        # Validate required headers
        if not filename:
            log.warning("Demo upload rejected: Missing MatchZy-FileName header")
            return jsonify({"error": "Missing MatchZy-FileName header"}), 400
        if not match_id:
            log.warning("Demo upload rejected: Missing MatchZy-MatchId header")
            return jsonify({"error": "Missing MatchZy-MatchId header"}), 400
        if map_number is None:
            log.warning("Demo upload rejected: Missing MatchZy-MapNumber header")
            return jsonify({"error": "Missing MatchZy-MapNumber header"}), 400

        # Validate filename (basic security check)
        if not filename.endswith('.zip') or '..' in filename or '/' in filename or '\\' in filename:
            log.warning(f"Demo upload rejected: Invalid filename: {filename}")
            return jsonify({"error": "Invalid filename"}), 400

        # Create demos directory structure
        demos_base_dir = Path(CS2_DEMO_DIRECTORY)
        match_dir = demos_base_dir / match_id
        match_dir.mkdir(parents=True, exist_ok=True)

        # Full path for the demo file
        demo_file_path = match_dir / filename

        # Check if file already exists
        if demo_file_path.exists():
            log.warning(f"Demo file already exists: {demo_file_path}")
            return jsonify({"error": "Demo file already exists"}), 409

        # Write the demo file
        try:
            with open(demo_file_path, 'wb') as f:
                # Read the request body in chunks to handle large files
                while True:
                    chunk = request.stream.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    f.write(chunk)

            file_size = demo_file_path.stat().st_size
            log.info(f"Demo uploaded successfully: {demo_file_path} ({file_size} bytes) - Match: {match_id}, Map: {map_number}")

            return jsonify({
                "status": "success",
                "message": "Demo uploaded successfully",
                "match_id": match_id,
                "map_number": int(map_number),
                "filename": filename,
                "file_size": file_size
            }), 200

        except OSError as file_error:
            log.error(f"Error writing demo file {demo_file_path}: {file_error}")
            # Clean up partial file if it exists
            if demo_file_path.exists():
                try:
                    demo_file_path.unlink()
                except:
                    pass
            return jsonify({"error": "Error writing demo file"}), 500

    except Exception as e:
        log.error(f"Error in upload_demo endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/download-demo')
def download_demo():
    """Download demo files for a specific match ID

    Query parameters:
    - matchid: The match ID to download demos for (required)

    Returns a ZIP file containing all demo files for the match, or individual file if only one exists.
    """
    try:
        match_id = request.args.get('matchid')

        # Validate required parameter
        if not match_id:
            return jsonify({"error": "matchid parameter is required"}), 400

        # Validate match_id (basic security check)
        if '..' in match_id or '/' in match_id or '\\' in match_id:
            log.warning(f"Demo download rejected: Invalid match_id: {match_id}")
            return jsonify({"error": "Invalid match_id"}), 400

        # Check if match directory exists
        demos_base_dir = Path(CS2_DEMO_DIRECTORY)
        match_dir = demos_base_dir / match_id

        if not match_dir.exists() or not match_dir.is_dir():
            log.info(f"Demo download requested for non-existent match: {match_id}")
            return jsonify({"error": "No demos found for this match"}), 404

        # Find all demo files in the match directory
        demo_files = list(match_dir.glob("*.zip"))

        if not demo_files:
            log.info(f"Demo download requested but no .zip files found for match: {match_id}")
            return jsonify({"error": "No demo files found for this match"}), 404

        # If only one demo file, send it directly
        if len(demo_files) == 1:
            demo_file = demo_files[0]
            log.info(f"Serving single demo file: {demo_file} for match: {match_id}")
            return send_file(
                demo_file,
                as_attachment=True,
                download_name=demo_file.name,
                mimetype='application/zip'
            )

        # If multiple demo files, create a temporary ZIP containing all of them
        import tempfile
        import zipfile

        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for demo_file in demo_files:
                    zipf.write(demo_file, demo_file.name)

            log.info(f"Serving combined ZIP with {len(demo_files)} demo files for match: {match_id}")
            return send_file(
                temp_zip.name,
                as_attachment=True,
                download_name=f"match_{match_id}_demos.zip",
                mimetype='application/zip'
            )

    except Exception as e:
        log.error(f"Error in download_demo endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5757, debug=False)
