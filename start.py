import asyncio
import asyncpg
import aiohttp

import utils

from src.bot import NASABot

config = utils.Configuration.get_config()

if utils.test_database_conn(config.db_uri):
    uri = config.db_uri
elif utils.test_database_conn(config.dev_uri):
    uri = config.dev_uri

async def run():
    async with asyncpg.create_pool(
        uri
    ) as pool, aiohttp.ClientSession() as session:
        async with NASABot(pool, session, config) as bot:
            await bot.create_tables()
            await bot.start(config.token)  # type: ignore


asyncio.run(run())
