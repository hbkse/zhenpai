from dotenv import load_dotenv
import os

"""
For local dev, env gets loaded from .env file
For deployment, env gets loaded from Railway
"""
load_dotenv()

# Required bot config
DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
OWNER_ID: int = int(os.environ.get('OWNER_ID'))
TESTING_GUILD_ID: int = int(os.getenv('TESTING_GUILD_ID'))

# Database config
DATABASE_URL = os.environ.get('DATABASE_URL')
PGDATABASE = os.environ.get('PGDATABASE')
PGHOST = os.environ.get('PGHOST')
PGPORT = os.environ.get('PGPORT')
PGUSER = os.environ.get('PGUSER')
PGPASSWORD = os.environ.get('PGPASSWORD')

# MySQL config for CS2 match data
MYSQL_HOST = os.environ.get('MYSQL_HOST')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
MYSQL_USER = os.environ.get('MYSQL_USER')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE')

# cogs.points
CS2_POINTS_GRAPH_URL = os.environ.get('CS2_POINTS_GRAPH_URL')

# cogs.cs2
LIVE_MATCH_CHANNEL_ID = int(os.environ.get('LIVE_MATCH_CHANNEL_ID'))
GUELO_TEAMS_JSON_URL = os.environ.get('GUELO_TEAMS_JSON_URL')

# Demo storage
CS2_DEMO_DIRECTORY = os.environ.get('CS2_DEMO_DIRECTORY', './demos')

# Flask app config for external access
FLASK_APP_HOST = os.environ.get('FLASK_APP_HOST', 'localhost:5757')
FLASK_APP_PROTOCOL = os.environ.get('FLASK_APP_PROTOCOL', 'http')

COMMIT_HASH = os.environ.get('COMMIT_HASH') or os.environ.get('RAILWAY_GIT_COMMIT_SHA') or "local"

COMMAND_PREFIX = "!"

# apexlegendsstatus dot com
APEX_API_KEY = os.environ.get('APEX_API_KEY')

# Riot Games API
RIOT_API_KEY = os.environ.get('RIOT_API_KEY')

# TFT OP.GG
TFT_OP_GG_BASE_URL = os.environ.get('TFT_OP_GG_BASE_URL', 'https://tft.op.gg')