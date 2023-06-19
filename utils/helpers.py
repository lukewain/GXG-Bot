from __future__ import annotations

import discord

from dataclasses import dataclass
import asyncpg
import json

from src.bot import GXGInteraction

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

        return cls(**results)

    async def validate_warn_threshold(
        self, interaction: GXGInteraction, user: discord.Member
    ) -> bool:
        res: int = await interaction.pool.fetchval(
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
    timestamp: int
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
        query = "SELECT * FROM moderationlog WHERE moderator_id=$1 ORDER BY timestamp DESC LIMIT 10"

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
            "Perpertrator": f"<@{self.moderatee_id}>",
            "Action": self.action,
            "Reason": self.reason,
        }
        for k, v in fields:
            embed.add_field(name=k, value=v, inline=False)

        return embed
