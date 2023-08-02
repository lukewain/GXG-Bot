import discord
from discord.ext import commands

from pprint import pprint

from src.bot import NASABot
from .errorlog import ErrorLog


class CustomEventHandler(commands.Cog):
    def __init__(self, bot: NASABot):
        self.bot = bot

    @commands.Cog.listener("on_errorlog_create")
    async def handle_error_webhook(self, errorlog: ErrorLog):
        if self.bot.error_webhook is None:
            return

        try:
            await self.bot.error_webhook.send(embed=errorlog.embed)
        except discord.HTTPException as e:
            return

    @commands.Cog.listener("on_interaction")
    async def delete_me(self, inter: discord.Interaction):
        pprint(inter.data)


async def setup(bot: NASABot):
    await bot.add_cog(CustomEventHandler(bot))
