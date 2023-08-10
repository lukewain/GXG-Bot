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

        await ctx.reply(f"```{d[:15]}```")

    @commands.commmand(name="stdout")
    async def stdout(self, ctx: NASAContext):
        ...
