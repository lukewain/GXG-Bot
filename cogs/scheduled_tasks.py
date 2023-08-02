import discord
from discord.ext import commands, tasks

from bs4 import BeautifulSoup
from logging import getLogger

import src

_poll_rate: int = 15  # Number of minutes for each update task

logger = getLogger("NASA.scheduledtasks")


class ScheduledTasks(commands.Cog):
    def __init__(self, bot: src.NASABot):
        self.bot = bot

    async def cog_load(self):
        self.update_member_count.start()
        self.update_tiktok_followers.start()

    @tasks.loop(minutes=_poll_rate)
    async def update_tiktok_followers(self):
        logger.info("Updating tiktok followers")
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86-64; rv:90.0) Gecko/20100101 Firefox/90.0"
        }

        response = await self.bot.session.get(
            "https://tiktok.com/@jayd3nn.x", headers=headers
        )

        txt_res = await response.read()

        soup = BeautifulSoup(txt_res, "html.parser")

        follower_count = soup.select_one('[title="Followers"]').text

        await self.bot.tiktok_channel.edit(name=f"Tiktok Followers: {follower_count}")

    @update_tiktok_followers.before_loop
    async def before_tiktok(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=_poll_rate)
    async def update_member_count(self):
        logger.info("Updating member count")
        # Get member count from guild
        guild = self.bot.get_guild(1064589769671192668)
        if not guild:
            guild = await self.bot.fetch_guild(1064589769671192668)

        total = guild.member_count

        await self.bot.member_channel.edit(name=f"Discord Members: {total}")

    @update_member_count.before_loop
    async def before_tiktok(self):
        await self.bot.wait_until_ready()


async def setup(bot: src.NASABot):
    await bot.add_cog(ScheduledTasks(bot))
