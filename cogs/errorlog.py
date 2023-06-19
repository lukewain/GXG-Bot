from __future__ import annotations

import datetime
import io
import logging
from dataclasses import dataclass

import asyncpg
import discord
from discord.ext import commands

from src.bot import GXGBot, GXGContext

_logger = logging.getLogger("ErrorLogHandler")


@dataclass
class ErrorLog:
    id: int
    unixtimestamp: int
    traceback: str
    item: str

    @classmethod
    async def get_or_none(cls, pool: asyncpg.Pool, id: int, /) -> ErrorLog | None:
        res = await pool.fetchrow("SELECT * FROM errorlog WHERE id=$1", id)

        return cls(**res) if res is not None else None

    @classmethod
    async def create(cls, pool: asyncpg.Pool, *, traceback: str, item: str):
        now_utc = int(discord.utils.utcnow().timestamp())
        res = await pool.fetchrow(
            "INSERT INTO errorlog (unixtimestamp, traceback, item) VALUES ($1, $2, $3) RETURNING *",
            now_utc,
            traceback,
            item,
        )

        return cls(**res)

    @classmethod
    async def delete(cls, pool: asyncpg.Pool, id: int, /):
        await pool.execute("DELETE FROM errorlog WHERE id=$1", id)

        return await pool.fetchval("SELECT count(*) FROM errorlog")

    @classmethod
    async def get_most_recent(
        cls, pool: asyncpg.Pool, num_to_get: int, /
    ) -> list[ErrorLog] | None:
        logs = await pool.fetch(
            "SELECT * FROM errorlog ORDER BY id DESC LIMIT $1", num_to_get
        )

        return [cls(**res) for res in logs] if logs else None

    @property
    def timestamp(self) -> datetime.datetime:
        """Returns a UTC datetime representing time of deletion"""
        return datetime.datetime.fromtimestamp(
            self.unixtimestamp, tz=datetime.timezone.utc
        )

    @property
    def embed(self) -> discord.Embed:
        """Generates an embed that represents this error

        Returns
        -------
        discord.Embed
            The generated Embed
        """

        embed = discord.Embed(
            title=f"Error #{self.id}{f' (Item/Command {self.item})' if self.item is not None else ''}",
            colour=discord.Colour.blue(),
        )
        embed.description = f"```{self.traceback[:5500]}```"
        embed.set_footer(
            text=f"Occurred On: {self.timestamp:%d:%m:%Y} at {self.timestamp:%I:%M:%M %p} UTC"
        )

        return embed

    @property
    def pub_embed(self) -> discord.Embed:
        """Returns the public embed message for this error

        Returns
        -------
        discord.Embed
            The generated Embed
        """
        return discord.Embed(
            title=f"An unexpected error occurred (ID: {self.id})",
            description=f"My developers are aware of the issue.\n\nIf you want to discuss this error with my developer, message @lukeee_w and refer to the error by it's id. (ID: {self.id})",
            color=discord.Color.blue(),
        )

    @property
    def raw_text(self) -> str:
        """Returns the error in a raw text buffer."""
        output = (
            f"Error #{self.id}{f' (Item/Command: {self.item})' if self.item is not None else ''}\n"
            f"Occurred On: {self.timestamp:%m-%d-%Y} at {self.timestamp:%I:%M:%M %p} UTC\n"
            f"{self.traceback}\n"
        )
        return output

    @property
    def raw_bytes(self) -> io.BytesIO:
        """Returns the error as a UTF-8 encoded bytes buffer."""
        output = io.BytesIO(self.raw_text.encode("UTF-8"))
        output.seek(0)

        return output


class ErrorLogCog(commands.Cog):
    def __init__(self, bot: GXGBot):
        self.bot = bot

    @commands.command(aliases=["e"])
    @commands.is_owner()
    async def error(self, ctx: GXGContext, error_id: int, raw: bool = False) -> None:
        """Sends an error from the database.

        Parameters
        ----------
        error_id: int
            The error id to send
        raw: bool
            Whether to send the error in raw form. Defaults to False
        """

        err = await ErrorLog.get_or_none(ctx.bot.pool, error_id)
        if not err:
            await ctx.send(f"I could not an error with that id. (ID: {error_id})")
            return
        if raw:
            await ctx.send(
                file=discord.File(err.raw_bytes, filename=f"{err.id} raw.txt")
            )
        else:
            await ctx.send(embed=err.embed)

    @commands.command(aliases=["re"])
    @commands.is_owner()
    async def recenterrors(self, ctx: GXGContext) -> None:
        """Returns the 20 most recently logged errors."""
        errs = await ErrorLog.get_most_recent(ctx.bot.pool, 20)
        embed = discord.Embed(color=discord.Color.blue(), description="")
        if errs:
            for err in errs:
                embed.description += f"{err.id:0>5}: (Item: {err.item}) {err.timestamp:%d-%m-%Y} at {err.timestamp:%I:%M:%M %p} UTC \n\n"  # type: ignore
            await ctx.send(embed=embed)
        else:
            await ctx.send("No errors logged yet.")


async def setup(bot: GXGBot):
    _logger.info("Loading cog ErrorLogCog")
    await bot.add_cog(ErrorLogCog(bot))
