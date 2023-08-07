import discord
from discord.ext import commands

import src


class EmergentEvents(commands.Cog):
    def __init__(self, bot: src.NASABot):
        self.bot = bot

    @commands.Cog.listener("on_voice_state_update")
    async def check_if_empty(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if len(before.channel.members) == 0:
            await self.bot.error_webhook.send(
                f"<@268815279570681857> {before.channel.name} is empty"
            )
