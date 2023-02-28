from dotenv import load_dotenv
import os

"""
For local dev, load env from file.
For deployment, handle in github action workflow + secrets.
"""
if os.environ.get('ENV') != 'CI':
    load_dotenv()

DISCORD_BOT_TOKEN = os.environ['DISCORD_BOT_TOKEN']
OWNER_ID = os.environ['OWNER_ID']
TWITCAST_CLIENT_ID = os.environ['TWITCAST_CLIENT_ID']
TWITCAST_CLIENT_SECRET = os.environ['TWITCAST_CLIENT_SECRET']
TWITCAST_ACCESS_TOKEN = os.environ['TWITCAST_ACCESS_TOKEN']

COMMIT_HASH = os.environ.get('COMMIT_HASH') or "local"

COMMAND_PREFIX = "z!"
LOGS_DIRECTORY = 'data/logs/'