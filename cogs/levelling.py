import discord
from discord.ext import commands

import typing

import utils
from src.bot import NASABot, NASAContext, NASAInteraction


# Checks
# --------------------------------
def is_blacklisted():
    async def predicate(ctx: NASAContext) -> bool:
        blusr = await utils.BlacklistedUser.fetch(ctx.bot.pool, ctx.author.id)
        if blusr:
            return False
        else:
            return True

    return commands.check(predicate)


class Levelling(commands.Cog):
    def __init__(self, bot: NASABot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def handle_user_message(self, message: discord.Message):
        await self.bot.level_manager.process_message(message)

    @commands.Cog.listener("on_member_level_up")
    async def member_levelup(self, member: utils.NASAMember):
        chnl: discord.abc.Messageable = self.bot.get_channel(self.bot.config.level_up_channel)  # type: ignore
        if not chnl:
            chnl = await self.bot.fetch_channel(self.bot.config.level_up_channel)  # type: ignore
        user = self.bot.get_user(member.id)
        if not user:
            user = await self.bot.fetch_user(member.id)

        await chnl.send(
            f"Congrats {user.mention}! You just advanced to level {member.level}"
        )

    # Commands
    # --------------------------------

    @commands.hybrid_group(name="rank")
    @is_blacklisted()
    async def rank(self, ctx: NASAContext, user: typing.Optional[discord.Member]):
        if user:
            data = user
        else:
            data = ctx.author
        member = await self.bot.level_manager.fetch_user(data)
        if member:
            await ctx.reply(embed=member.rank_embed)
        else:
            await ctx.reply(content="You are not yet ranked")


async def setup(bot: NASABot):
    await bot.add_cog(Levelling(bot))
