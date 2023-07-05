import asyncio
import asyncpg
import aiohttp
import os

import utils

from src.bot import GXGBot

__import__("dotenv").load_dotenv()

config = utils.Configuration.get_config()


async def run():
    async with asyncpg.create_pool(
        config.db_uri
    ) as pool, aiohttp.ClientSession() as session:
        async with GXGBot(pool, session, config) as bot:
            await bot.create_tables()
            await bot.start(config.token)  # type: ignore


asyncio.run(run())
