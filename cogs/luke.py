import discord
from discord.ext import commands

from src import *


class LogCommands(commands.Cog):
    def __init__(self, bot: NASABot):
        self.bot = bot

    @commands.command(name="logs")
    async def logs(self, ctx: NASAContext):
        with open(self.bot.error_log_file) as el:
            d = el.readlines()

        formatted = d[-20:]

        string = "".join(formatted)

        await ctx.reply(f"```{discord.utils.escape_markdown(string)}```")

    @commands.command(name="stdout")
    async def stdout(self, ctx: NASAContext):
        with open(self.bot.stdout_log_file) as sl:
            d = sl.readlines()

        formatted = d[-20:]

        string = "".join(formatted)

        await ctx.reply(f"```{discord.utils.escape_markdown(string)}```")


async def setup(bot: NASABot):
    await bot.add_cog(LogCommands(bot))
