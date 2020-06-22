import asyncio
from aiohttp import web

app = web.Application()


async def run_server():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()


def start_server():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_server())
