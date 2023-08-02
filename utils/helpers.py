from __future__ import annotations

import discord

from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncpg
import json

from typing import Optional, Self

# from src.bot import NASAInteraction

__all__ = (
    "ModerationLog",
    "Configuration",
    "Muted",
    "Warning",
    "BlacklistedUser",
    "Mode",
    "test_database_conn",
)


class Mode(Enum):
    "Unrated"
    "Competitive"
    "Other"


@dataclass
class Configuration:
    warn_threshold: int | None
    log_channel_id: int | None
    log_webhook_url: str | None
    modmail_forum_id: int | None
    token: str | None
    dev_uri: str
    db_uri: str | None
    henrikdev_token: str
    mute_role_id: int | None
    error_webhook_url: str | None
    level_up_channel: int
    lfg_channel: int | None
    tiktok_channel: int
    member_channel: int
    join_to_create_ids: list[int] | None

    @classmethod
    def get_config(cls, /) -> Configuration:
        with open("config.json") as config:
            data = json.load(config)

        return cls(**data)

    def _update_value(self, item, value) -> Configuration | None:
        try:
            with open("config.json") as config:
                data: dict = json.load(config)

            data[item]

            data[item] = value

            return self.__init__(**data)

        except KeyError:
            return None

    def update_log_id(self, _id: int):
        self.log_channel_id = _id

        self.save()

    def update_log_url(self, uri: str) -> Configuration:
        self._update_value("log_webhook_url", uri)

        return self

    def update_join_to_create(self, _id: int):
        if self.join_to_create_ids is None:
            self.join_to_create_ids = [_id]
        else:
            self.join_to_create_ids.append(_id)

        self.save()

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

    def save(self):
        items = self.__dict__
        with open("config.json", "w") as config:
            json.dump(items, config, indent=4)

    def close(self):
        self.save()


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
    warning_id: int
    user_id: int
    reason: str
    unixtimestamp: int
    total_warnings: int

    @classmethod
    async def add(cls, pool: asyncpg.Pool, user_id: int, reason: str) -> Warning:
        res = await pool.fetchrow("SELECT * FROM warnings WHERE id=$1", id)

        if res:
            r = await pool.fetchrow(
                "INSERT INTO WARNINGS (user_id, reason, unixtimestamp) RETURNING *",
                reason,
                id,
            )
        else:
            r = await pool.fetchrow(
                "INSERT INTO warnings (id, infractions, infraction_reasons) VALUES ($1, $2, $3) RETURNING *",
                id,
                1,
                [reason],
            )

        tw = await pool.fetchval(
            "SELECT count(*) FROM warnings WHERE user_id=$1", user_id
        )

        data = {**res, "total_warnings": tw}

        return cls(**data)

    @classmethod
    async def fetch(cls, pool: asyncpg.Pool, warn_id: int) -> Warning | None:
        """
        |coro|

        Fetches a warning from the database"""
        res = await pool.fetchrow("SELECT * FROM warnings WHERE warning_id=$1", id)

        if not res:
            return None

        else:
            return cls(**res)

    @classmethod
    async def remove(cls, pool: asyncpg.Pool, *, warn_id: int) -> bool:
        """
        |coro|

        Removes a warning from the database.

        Parameters
        ----------
        pool: `asyncpg.Pool`
            The database pool to use
        warn_id: `int`
            The id to remove

        Returns
        -------
        `True`
            If the warning is deleted
        `False`
            If the warning does not exist
        """

        res = await pool.fetchrow("SELECT * FROM warnings WHERE warning_id=$1", warn_id)

        if not res:
            return False

        else:
            await pool.execute("DELETE FROM warnings WHERE warning_id=$1", warn_id)

            return True


@dataclass
class BlacklistedUser:
    id: int
    moderator_id: int
    added_at: int
    in_server: bool

    @classmethod
    async def create(
        cls, pool: asyncpg.Pool, user_id: int, moderator_id: int
    ) -> BlacklistedUser:
        query = "INSERT INTO blacklist (id, moderator_id, added_at) VALUES ($1, $2, $3) RETURNING * ON CONFLICT (id) DO SELECT * FROM blacklist WHERE id=$1"

        res = await pool.fetchrow(
            query, user_id, moderator_id, round(datetime.now().timestamp())
        )

        return cls(**res)

    @classmethod
    async def fetch(cls, pool: asyncpg.Pool, user_id: int) -> BlacklistedUser | None:
        query = "SELECT * FROM blacklist WHERE id=$1"

        res = await pool.fetchrow(query, user_id)

        if res:
            return cls(**res)
        else:
            return None


@dataclass
class LFGEntry:
    id: int
    msg_id: int
    author_id: int
    gamemode: str
    players: list[int]
    expires_at: int

    @classmethod
    async def create(
        cls,
        pool: asyncpg.Pool,
        message_id: int,
        author_id: int,
        gamemode: str,
        players: list[str],
    ):
        ...

    @property
    def mentioned_players(self) -> str:
        """
        Returns a string with `\n` separated mentioned players
        """
        pstring = ""
        for _ in self.players:
            pstring += f"<@{_}>\n"

        return pstring

    @property
    def embed(self) -> discord.Embed:
        embed = discord.Embed(title="Looking for ")

        return embed


async def test_database_conn(uri: str) -> bool:
    try:
        pool = asyncpg.Pool(uri)
        return True
    except ConnectionRefusedError:
        return False
