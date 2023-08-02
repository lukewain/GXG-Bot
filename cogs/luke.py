from __future__ import annotations

import discord
from discord.ext import commands

from datetime import datetime, timezone
import typing
import sys
import os
from importlib.metadata import distribution, packages_distributions
from jishaku.math import natural_size
from jishaku.modules import package_version

try:
    import psutil
except ImportError:
    psutil = None

from src.bot import NASABot, NASAContext


class Luke(commands.Cog):
    def __init__(self, bot: NASABot):
        self.bot: NASABot = bot

    async def cog_load(self):
        self.start_time = datetime.utcnow().replace(tzinfo=timezone.utc)

    # Commands
    # --------

    @commands.group(name="dev", invoke_without_command=True)
    @commands.is_owner()
    async def dev(self, ctx: NASAContext):
        distributions: typing.List[str] = [
            dist
            for dist in packages_distributions()["discord"]  # type: ignore
            if any(
                file.parts == ("discord", "__init__.py")  # type: ignore
                for file in distribution(dist).files  # type: ignore
            )
        ]

        if distributions:
            dist_version = f"{distributions[0]} `{package_version(distributions[0])}`"
        else:
            dist_version = f"unknown `{discord.__version__}`"

        summary = [
            f"`Python {sys.version}` on `{sys.platform}`".replace("\n", ""),
            f"Cog was loaded <t:{self.start_time.timestamp():.0f}:R>.",
            "",
        ]

        # detect if [procinfo] feature is installed
        if psutil:
            try:
                proc = psutil.Process()

                with proc.oneshot():
                    try:
                        mem = proc.memory_full_info()
                        summary.append(
                            f"Using {natural_size(mem.rss)} physical memory and "
                            f"{natural_size(mem.vms)} virtual memory, "
                            f"{natural_size(mem.uss)} of which unique to this process."
                        )
                    except psutil.AccessDenied:
                        pass

                    try:
                        name = proc.name()
                        pid = proc.pid
                        thread_count = proc.num_threads()

                        summary.append(
                            f"Running on PID {pid} (`{name}`) with {thread_count} thread(s)."
                        )
                    except psutil.AccessDenied:
                        pass

                    summary.append("")  # blank line
            except psutil.AccessDenied:
                summary.append(
                    "psutil is installed, but this process does not have high enough access rights "
                    "to query process information."
                )
                summary.append("")  # blank line
        s_for_guilds = "" if len(self.bot.guilds) == 1 else "s"
        s_for_users = "" if len(self.bot.users) == 1 else "s"
        cache_summary = f"{len(self.bot.guilds)} guild{s_for_guilds} and {len(self.bot.users)} user{s_for_users}"

        # Show shard settings to summary
        if isinstance(self.bot, discord.AutoShardedClient):
            if len(self.bot.shards) > 20:
                summary.append(
                    f"This bot is automatically sharded ({len(self.bot.shards)} shards of {self.bot.shard_count})"
                    f" and can see {cache_summary}."
                )
            else:
                shard_ids = ", ".join(str(i) for i in self.bot.shards.keys())
                summary.append(
                    f"This bot is automatically sharded (Shards {shard_ids} of {self.bot.shard_count})"
                    f" and can see {cache_summary}."
                )
        elif self.bot.shard_count:
            summary.append(
                f"This bot is manually sharded (Shard {self.bot.shard_id} of {self.bot.shard_count})"
                f" and can see {cache_summary}."
            )
        else:
            summary.append(f"This bot is not sharded and can see {cache_summary}.")

        # pylint: disable=protected-access
        if self.bot._connection.max_messages:  # type: ignore
            message_cache = f"Message cache capped at {self.bot._connection.max_messages}"  # type: ignore
        else:
            message_cache = "Message cache is disabled"

        remarks = {True: "enabled", False: "disabled", None: "unknown"}

        *group, last = (
            f"{intent.replace('_', ' ')} intent is {remarks.get(getattr(self.bot.intents, intent, None))}"
            for intent in ("presences", "members", "message_content")
        )

        summary.append(f"{message_cache}, {', '.join(group)}, and {last}.")

        # pylint: enable=protected-access

        # Show websocket latency in milliseconds
        summary.append(
            f"Average websocket latency: {round(self.bot.latency * 1000, 2)}ms"
        )

        await ctx.send("\n".join(summary))

    @dev.command(name="load")
    @commands.is_owner()
    async def dev_load(self, ctx: NASAContext, *, cog_name: str):
        cog_name = "cogs." + cog_name
        try:
            await self.bot.load_extension(cog_name)
            await ctx.send(f"\U00002705 Loaded {cog_name}")
        except commands.ExtensionNotFound:
            await ctx.send("Whoops, this extension was not found")

    @dev.command(name="reload")
    @commands.is_owner()
    async def dev_reload(self, ctx: NASAContext, *, cog_name: str):
        cog_name = "cogs." + cog_name
        try:
            await self.bot.reload_extension(cog_name)
            await ctx.send(f"\U00002705 Reloaded {cog_name}")
        except commands.ExtensionNotFound:
            await ctx.send("Whoops, this extension was not found")
        except commands.ExtensionNotLoaded:
            await ctx.send("Woah, this extension is not loaded!")

    @dev.command(name="unload")
    @commands.is_owner()
    async def dev_unload(self, ctx: NASAContext, *, cog_name: str):
        cog_name = "cogs." + cog_name
        try:
            await self.bot.unload_extension(cog_name)
            await ctx.send(f"\U00002705 Unloaded {cog_name}")
        except commands.ExtensionNotFound:
            await ctx.send(f"Whoops, this extension was not found")
        except commands.ExtensionNotLoaded:
            await ctx.send("Woah, this extension was not loaded!")

    @dev.command(name="reset")
    @commands.is_owner()
    async def dev_reset(self, ctx: NASAContext, *, user: discord.Member):
        userprofile = await ctx.bot.level_manager.fetch_user(user)

        if not userprofile:
            await ctx.send("User does not have a profile, cannot reset")

        else:
            await ctx.bot.pool.execute("DELETE FROM levels WHERE id=$1", user.id)
            await ctx.send(f"Reset {str(user)}'s levelling data")

    @dev.command(name="list")
    @commands.is_owner()
    async def dev_list_all_cogs(self, ctx: NASAContext):
        cogslist = [f[:-3] for f in os.listdir("./cogs") if f.endswith(".py")]
        cogstext = "\n".join(cogslist)
        await ctx.send(f"Cog list ```{cogstext}```")


async def setup(bot: NASABot):
    await bot.add_cog(Luke(bot))
