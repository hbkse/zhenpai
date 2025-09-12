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

# cogs.cs2
LIVE_MATCH_CHANNEL_ID = int(os.environ.get('LIVE_MATCH_CHANNEL_ID'))
GUELO_TEAMS_JSON_URL = os.environ.get('GUELO_TEAMS_JSON_URL')

COMMIT_HASH = os.environ.get('COMMIT_HASH') or os.environ.get('RAILWAY_GIT_COMMIT_SHA') or "local"

COMMAND_PREFIX = "!"

# apexlegendsstatus dot com 
APEX_API_KEY = os.environ.get('APEX_API_KEY')