from dotenv import load_dotenv
import os

"""
For local dev, load env from file.
For deployment, handle in github action workflow + secrets.
"""
load_dotenv()

DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
OWNER_ID: int = int(os.environ.get('OWNER_ID'))
TWITCAST_CLIENT_ID = os.environ.get('TWITCAST_CLIENT_ID') or ''
TWITCAST_CLIENT_SECRET = os.environ.get('TWITCAST_CLIENT_SECRET') or ''
TWITCAST_ACCESS_TOKEN = os.environ.get('TWITCAST_ACCESS_TOKEN') or ''

COMMIT_HASH = os.environ.get('COMMIT_HASH') or os.environ.get('RAILWAY_GIT_COMMIT_SHA') or "local"

COMMAND_PREFIX = "!"