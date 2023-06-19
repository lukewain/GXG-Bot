from __future__ import annotations
from dataclasses import dataclass

import discord
from discord.ext import commands

import asyncpg
import aiohttp
import logging
from typing import List

import utils

__import__("dotenv").load_dotenv()

discord.utils.setup_logging()
_logger = logging.getLogger("GXGBot")


@dataclass()
class GXGMember:
    id: int
    xp: int
    modifier: float
    last_gained: int


class GXGContext(commands.Context["GXGBot"]):
    """
    A placeholder for the regular commands.Context
    """

    ...


class GXGInteraction(discord.Interaction):
    """
    A placeholder for the regular discord.Interaction
    """

    client: GXGBot

    pool: asyncpg.Pool = client.pool  # type: ignore


class GXGBot(commands.Bot):
    def __init__(self, pool: asyncpg.Pool, session: aiohttp.ClientSession):
        self.pool: asyncpg.Pool = pool
        self.session = session

        self.config = utils.Configuration.get_config()

        intents = discord.Intents.default()
        intents.message_content = True

        self.owner_ids = (874953578509381652, 268815279570681857)

        super().__init__(command_prefix="gxg.", intents=intents)

    async def get_context(self, message, *, cls=GXGContext):
        # when you override this method, you pass your new Context
        # subclass to the super() method, which tells the bot to
        # use the new MyContext class
        return await super().get_context(message, cls=cls)

    async def create_tables(self):
        """
        |coro|

        Creates the tables in the database from the schema.sql file
        """
        _logger.info("Creating tables")
        with open("schema.sql") as data:
            await self.pool.execute(data.read())
        _logger.info("Tables created")

    async def get_member(
        self, member: discord.Member | discord.User
    ) -> GXGMember | None:
        """
        |coro|

        Get's the members info from the database

        This does not have a cache but is not a resource intensive operation

        Paramaters
        ----------

        member: discord.Member | discord.User
            The member to get the information of

        Returns
        -------
        `GXGMember` or `None` depending on the data
        """

        _logger.debug("Running func [get_member]")

        res: asyncpg.Record = await self.pool.fetchrow(
            "SELECT * FROM users WHERE id=$1", member.id
        )

        if res is None:
            return None

        else:
            return GXGMember(**res)

    async def setup_hook(self):
        self.immune = []
        res: List[asyncpg.Record] = await self.pool.fetch("SELECT * FROM immune")

        for r in res:
            self.immune.append(r["id"])

        await self.load_extension("jishaku")
        await self.load_extension("cogs.errorlog")
        await self.load_extension("cogs.error_handler")

    async def on_ready(self):
        _logger.info(f"Logged in as {self.user}")
