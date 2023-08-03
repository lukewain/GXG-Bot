from __future__ import annotations
from dataclasses import dataclass
import datetime
from logging import config

import discord
from discord.ext import commands

import asyncpg
import aiohttp
import logging
from typing import List, Self

import utils

__all__ = ("NASABot", "NASAContext", "NASAInteraction")

discord.utils.setup_logging()
_logger = logging.getLogger("NASABot")


class NASAContext(commands.Context["NASABot"]):
    """
    A placeholder for the regular commands.Context
    """


class NASAInteraction(discord.Interaction["NASABot"]):
    """
    A placeholder for the regular discord.Interaction
    """

    # pool: asyncpg.Pool = client.pool


class NASABot(commands.Bot):
    def __init__(
        self,
        pool: asyncpg.Pool,
        session: aiohttp.ClientSession,
        config: utils.Configuration,
    ):
        self.pool: asyncpg.Pool = pool
        self.session = session
        self.level_manager = utils.LevelManager(self.pool, self)
        self.config = config

        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        self.owner_id = 268815279570681857

        super().__init__(
            command_prefix=".",
            intents=intents,
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=True, roles=True, replied_user=True
            ),
        )

    async def get_context(self, message, *, cls=NASAContext):
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

    async def get_or_fetch(self, user: int) -> discord.Member | discord.User:
        m = self.get_user(user)
        if not m:
            m = self.fetch_user(user)

        return m

    async def setup_hook(self):
        # Set up the level manager
        await self.level_manager.start()

        self.immune = []
        res: List[asyncpg.Record] = await self.pool.fetch("SELECT * FROM immune")

        for r in res:
            self.immune.append(r["id"])

        if self.config.error_webhook_url:
            self.error_webhook = discord.Webhook.from_url(
                self.config.error_webhook_url, session=self.session
            )
        else:
            self.error_webhook = None

        await self.load_extension("jishaku")
        await self.load_extension("cogs.errorlog")
        await self.load_extension("cogs.error_handler")
        await self.load_extension("cogs.modmail")
        await self.load_extension("cogs.voices")
        await self.load_extension("cogs.scheduled_tasks")
        await self.load_extension("cogs.custom_event_handler")
        await self.load_extension("cogs.levelling")
        # await self.load_extension("cogs.moderation")
        # await self.load_extension("cogs.testing")

        self.tiktok_channel = self.get_channel(self.config.tiktok_channel)
        if not self.tiktok_channel:
            self.tiktok_channel = await self.fetch_channel(self.config.tiktok_channel)

        self.member_channel = self.get_channel(self.config.member_channel)
        if not self.member_channel:
            self.member_channel = await self.fetch_channel(self.config.member_channel)

    async def on_ready(self):
        _logger.info(f"Logged in as {self.user}")

    async def close(self):
        await self.error_webhook.send(
            embed=discord.Embed(title="The bot is disconnected!"),
            content=f"<@{self.owner_id}>",
        )
        self.config.close()
        await super().close()
