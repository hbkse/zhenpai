import discord
import logging.config
import asyncio
import contextlib
from bot import Zhenpai
from logging.handlers import RotatingFileHandler
from aiohttp import ClientSession
import asyncpg
import config

def db_connection_options():
    return {
        'user': config.PGUSER,
        'password': config.PGPASSWORD,
        'database': config.PGDATABASE,
        'host': config.PGHOST,
        'port': config.PGPORT,
        'min_size': 2,
        'max_size': 8
    }

class RemoveNoise(logging.Filter):
    def __init__(self):
        super().__init__(name='discord.state')

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelname == 'WARNING' and 'referencing an unknown' in record.msg:
            return False
        return True

@contextlib.contextmanager
def setup_logging():
    log = logging.getLogger()

    try:
        discord.utils.setup_logging()
        # __enter__
        max_bytes = 32 * 1024 * 1024  # 32 MiB
        logging.getLogger('discord').setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.WARNING)
        logging.getLogger('discord.state').addFilter(RemoveNoise())

        log.setLevel(logging.INFO)
        handler = RotatingFileHandler(filename='info.log', encoding='utf-8', mode='w', maxBytes=max_bytes, backupCount=5)
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')
        handler.setFormatter(fmt)
        log.addHandler(handler)

        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for hdlr in handlers:
            hdlr.close()
            log.removeHandler(hdlr)

async def run_bot():
    async with ClientSession() as http_client:
        async with asyncpg.create_pool(**db_connection_options()) as pool:
            async with Zhenpai(http_client=http_client, db_pool=pool) as bot:
                await bot._run()

def main():
    with setup_logging():
        asyncio.run(run_bot())

if __name__ == '__main__':
    main()