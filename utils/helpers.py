from __future__ import annotations

import discord

from datetime import datetime
from dataclasses import dataclass
import asyncpg
import json

from typing import Optional

# from src.bot import GXGInteraction

__all__ = ("ModerationLog", "Configuration")


@dataclass
class Configuration:
    warn_threshold: int
    log_channel_id: int

    @classmethod
    def get_config(cls, /) -> Configuration:
        with open("config.json") as config:
            data = json.load(config)

        results = data.values()

        return cls(**data)

    async def validate_warn_threshold(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> bool:
        res: int = await interaction.pool.fetchval(  # type: ignore
            "SELECT infraction from warnings WHERE id=$1", user.id
        )

        if res == self.warn_threshold:
            return True
        else:
            return False


@dataclass
class ModerationLog:
    entry_id: int
    moderator_id: int
    unixtimestamp: int
    action: str
    reason: str
    moderatee_id: int

    @classmethod
    async def fetch_moderator_actions(
        cls, pool: asyncpg.Pool, id: int, /
    ) -> list[ModerationLog] | None:
        """
        |coro|

        Finds the 10 most recent moderation actions from the specified moderator

        Paramters
        ---------
        pool: `asyncpg.Pool`
            The client pool to use
        id: `int`
            The moderator id to find actions of
        """
        query = "SELECT * FROM moderationlog WHERE moderator_id=$1 ORDER BY unixtimestamp DESC LIMIT 10"

        res: list[asyncpg.Record] = await pool.fetch(query, id)

        if len(res) < 1:
            return None

        return [cls(**r) for r in res]

    @classmethod
    async def get_moderatee_logs(
        cls, pool: asyncpg.Pool, id: int, /
    ) -> list[ModerationLog] | None:
        """
        |coro|

        Finds all the moderation logs linked to a specific user

        Paramters
        ---------
        pool: `asyncpg.Pool`
            The client pool to use
        id: `int`
            The moderatee you want to view

        Returns
        -------
        `ModerationLog` or `None`
        """

        query = "SELECT * FROM moderationlog WHERE moderatee_id=$1 ORDER BY unixtimestamp DESC"

        res: list[asyncpg.Record] = await pool.fetch(query, id)

        if len(res) < 1:
            return None

        return [cls(**r) for r in res]

    @classmethod
    async def add_moderation_action(
        cls,
        pool: asyncpg.Pool,
        moderator_id: int,
        action: str,
        reason: str,
        moderatee_id: int,
        /,
    ) -> ModerationLog:
        query = "INSERT INTO moderationlog (moderator_id, unixtimestamp, action, reason, moderatee_id) VALUES ($1, $2, $3, $4, $5) RETURNING *"
        now_utc = int(discord.utils.utcnow().timestamp())
        res: asyncpg.Record = await pool.fetchrow(
            query, moderator_id, now_utc, action, reason, moderatee_id
        )

        return cls(**res)

    @classmethod
    async def fetch_moderator_action(
        cls, pool: asyncpg.Pool, entry_id: int
    ) -> ModerationLog | None:
        query = "SELECT * FROM moderationlog WHERE entry_id=$1"
        res: asyncpg.Record | None = await pool.fetchrow(query, entry_id)
        if not res:
            return None
        return cls(**res)

    @property
    def embed(self) -> discord.Embed:
        """Generates an embed that represents this action

        Returns
        -------
        `discord.Embed`
            The embed generated for this action"""

        embed = discord.Embed(
            title="New Moderation Action!",
        )
        fields = {
            "Moderator": f"<@{self.moderator_id}>",
            "User": f"<@{self.moderatee_id}>",
            "Action": self.action,
            "Reason": self.reason,
        }
        for k, v in fields:
            embed.add_field(name=k, value=v, inline=False)

        return embed


@dataclass
class Muted:
    mute_id: int
    id: int
    reason: Optional[str]
    duration: int
    expires: int
    expired: bool

    @classmethod
    async def fetch_next(cls, pool: asyncpg.Pool) -> Muted | None:
        now = round(datetime.now().timestamp())

        res: asyncpg.Record = await pool.fetchrow(
            "SELECT * FROM muted WHERE expires > $1 AND expired = $2 ORDER BY expires DESC LIMIT 1",
            now,
            False,
        )

        return cls(**res)

    @classmethod
    async def add_new(
        cls, pool: asyncpg.Pool, id: int, reason: Optional[str], duration: int
    ) -> Muted:
        query = (
            "INSERT INTO muted (id, reason, duration, expires) VALUES ($1, $2, $3, $4)"
        )

        now = round(datetime.now().timestamp())

        expiration = now + duration

        res: asyncpg.Record = await pool.fetchrow(
            query, id, reason, duration, expiration
        )

        return cls(**res)

    @classmethod
    async def check(cls, pool: asyncpg.Pool, id: int) -> Muted | None:
        query = "SELECT * FROM muted WHERE id=$1 AND expired=$2"

        res: asyncpg.Record | None = await pool.fetchrow(query, id, False)

        if not res:
            return None

        return cls(**res)

    @classmethod
    async def premature(cls, pool: asyncpg.Pool, id: int) -> Muted | None:
        query = "SELECT * FROM muted WHERE id=$1 and expired=$2"

        res: asyncpg.Record | None = await pool.fetchrow(query, id, False)

        if res:
            now = round(datetime.now().timestamp())
            query = (
                "UPDATE muted SET expired=$1, expires=$2 WHERE mute_id=$3 RETURNING *"
            )
            res2 = await pool.fetchrow(query, True, now, res["mute_id"])

            return cls(**res2)

        else:
            return None


@dataclass
class Warning:
    id: int
    infractions: int
    infraction_reasons: list[str]

    @classmethod
    async def add(cls, pool: asyncpg.Pool, id: int, reason: str) -> Warning:
        res = await pool.fetchrow("SELECT * FROM warnings WHERE id=$1", id)

        if res:
            data = await pool.fetchrow(
                "UPDATE warnings SET infractions = infractions + 1, infraction_reasons = array_append(infraction_reasons, $1) WHERE id=$2 RETURNING *",
                reason,
                id,
            )
        else:
            data = await pool.fetchrow(
                "INSERT INTO warnings (id, infractions, infraction_reasons) VALUES ($1, $2, $3) RETURNING *",
                id,
                1,
                [reason],
            )

        return cls(**data)

    @classmethod
    async def fetch(cls, pool: asyncpg.Pool, id: int) -> Warning | None:
        res = await pool.fetchrow("SELECT * FROM warnings WHERE id=$1", id)

        if not res:
            return None

        else:
            return cls(**res)
