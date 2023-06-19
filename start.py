import asyncio
import asyncpg
import aiohttp
import os

from src.bot import GXGBot

__import__("dotenv").load_dotenv()


async def run():
    async with asyncpg.create_pool(
        os.environ["DB_URI"]
    ) as pool, aiohttp.ClientSession() as session:
        async with GXGBot(pool, session) as bot:
            await bot.create_tables()
            await bot.start(os.environ["TOKEN"])


asyncio.run(run())
