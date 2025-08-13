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

COMMIT_HASH = os.environ.get('COMMIT_HASH') or os.environ.get('RAILWAY_GIT_COMMIT_SHA') or "local"

COMMAND_PREFIX = "!"

APEX_API_KEY = os.environ.get('APEX_API_KEY')