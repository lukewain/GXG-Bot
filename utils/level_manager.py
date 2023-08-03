import random
from typing import Self
import asyncpg
import datetime
from dataclasses import dataclass
from logging import getLogger

from src.bot import NASABot

import discord

logger = getLogger("NASA.levelmanager")


__all__ = ("NASAMember", "LevelManager")


@dataclass()
class NASAMember:
    id: int
    level: int
    overflow_xp: int
    modifier: float
    last_gained: int
    messages: int

    @property
    def rank_embed(self) -> discord.Embed:
        embed = discord.Embed(title="Current Rank")
        embed.colour = discord.Colour.from_str("#687198")

        xp_for_next = 5 * (self.level**2) + (50 * self.level) + 100 - self.overflow_xp

        embed.description = f"""```
Rank: {self.level}
XP to next: {xp_for_next} XP
Messages: {self.messages}```"""

        return embed


@dataclass()
class BlockedChannel:
    id: int
    type: str
    added_by: int


@dataclass()
class BlockedUser:
    id: int
    type: str
    added_by: int


class LevelManager:
    def __init__(self, pool: asyncpg.Pool, bot: NASABot):
        self._pool = pool
        self.bot: NASABot = bot

    async def start(self):
        """
        |coro|

        This starts the LevelManager.
        It initializes the caches
        """
        logger.info("Initializing level manager...")

        self._blocked_channels = list()
        self._blocked_members = list()

        # Get the members and channels where xp gain is blocked

        query = "SELECT * FROM xp_blocked"
        res = await self._pool.fetch(query)

        for entry in res:
            if entry["type"] == "channel":
                self._blocked_channels.append(BlockedChannel(**entry))
            elif entry["type"] == "user":
                self._blocked_members.append(BlockedUser(**entry))
            else:
                logger.error(f"Could not find type {entry['type']}")

        logger.info("Level Manager initialized.")

    def _fetch_list_ids(self, list_name):
        return [u.id for u in list_name]

    async def fetch_user(
        self, user: discord.User | discord.Member
    ) -> NASAMember | None:
        res = await self._pool.fetchrow("SELECT * FROM levels WHERE id=$1", user.id)

        if res:
            return NASAMember(**res)
        else:
            return None

    async def process_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.author.id in self._fetch_list_ids(self._blocked_members):
            return

        if message.channel.id in self._fetch_list_ids(self._blocked_channels):
            return

        # Fetch the user's xp info from database

        query = "SELECT * FROM levels WHERE id=$1"
        response = await self._pool.fetchrow(query, message.author.id)

        if not response:
            response = await self._pool.fetchrow(
                "INSERT INTO levels (id, overflow_xp, last_gained) VALUES ($1, $2, $3) RETURNING *",
                message.author.id,
                0,
                0,
            )

        member = NASAMember(**response)

        if member.last_gained > (round(message.created_at.timestamp()) - 60):
            await self._pool.execute(
                "UPDATE levels SET messages = messages + 1 WHERE id=$1",
                message.author.id,
            )
            return

        xp_gain = random.randint(5, 15)

        xp_gain *= member.modifier

        member.overflow_xp += round(xp_gain)

        # Calculate the new level of the member (if changed)

        xp_for_next = (
            5 * (member.level**2) + (50 * member.level) + 100 - member.overflow_xp
        )

        if xp_for_next <= member.overflow_xp:
            new_level = member.level + 1
            member.overflow_xp -= xp_for_next
        else:
            new_level = member.level

        if new_level > member.level:
            member.level = new_level
            self.bot.dispatch("member_level_up", member)

        # Update the new member information

        await self._pool.execute(
            "UPDATE levels SET messages = messages + 1, overflow_xp=$1, level=$2, last_gained=$3 WHERE id=$4",
            member.overflow_xp,
            member.level,
            round(datetime.datetime.now().timestamp()),
            member.id,
        )
