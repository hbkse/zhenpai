from dotenv import load_dotenv
import os

"""
For local dev, env gets loaded from .env file
For deployment, env gets loaded from Railway
"""
load_dotenv()

DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
OWNER_ID: int = int(os.environ.get('OWNER_ID'))
TESTING_GUILD_ID: int = int(os.getenv('TESTING_GUILD_ID'))

DATABASE_URL = os.environ.get('DATABASE_URL')
PGDATABASE = os.environ.get('PGDATABASE')
PGHOST = os.environ.get('PGHOST')
PGPORT = os.environ.get('PGPORT')
PGUSER = os.environ.get('PGUSER')
PGPASSWORD = os.environ.get('PGPASSWORD')

COMMIT_HASH = os.environ.get('COMMIT_HASH') or os.environ.get('RAILWAY_GIT_COMMIT_SHA') or "local"

# Twitcasting cog
TWITCAST_CLIENT_ID = os.environ.get('TWITCAST_CLIENT_ID') or ''
TWITCAST_CLIENT_SECRET = os.environ.get('TWITCAST_CLIENT_SECRET') or ''
TWITCAST_ACCESS_TOKEN = os.environ.get('TWITCAST_ACCESS_TOKEN') or ''

COMMAND_PREFIX = "!"