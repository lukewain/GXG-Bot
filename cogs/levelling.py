import discord
from discord import app_commands
from discord.ext import commands

import typing
from typing import NamedTuple
import asyncpg

# import aggdraw
# from PIL import Image, ImageDraw, ImageFilter, Imagefont
# from jishaku.functools import executor_function
import io
import itertools

import utils
from src.bot import NASABot, NASAContext, NASAInteraction


class DatabaseData(NamedTuple):
    id: int
    level: int
    overflow_xp: int
    modifier: float
    last_gained: int
    messages: int
    rank: int


class RankCard:
    # Options
    WIDTH = 1200
    HEIGHT = 400
    RANKBAR_HEIGHT = 25
    OVERALL_PADDING = 50
    AVATAR_BORDER_MARGIN = 10
    LEFT_TEXT_PADDING_L = 25
    AUTHOR_NAME_PADDING_RIGHT = 50
    BOTTOM_CORNER_FONT_PADDING = 50

    DROP_SHADOW_OFFSET = (3, 3)
    DROP_SHADOW_ITERATIONS = 15
    DROP_SHADOW_EXTRA_SIZE = 10

    # Calculations
    AVATAR_SIZE = (
        HEIGHT - RANKBAR_HEIGHT - ((OVERALL_PADDING + AVATAR_BORDER_MARGIN) * 2)
    )
    AVATAR_BORDER_SIZE = HEIGHT - RANKBAR_HEIGHT - (OVERALL_PADDING * 2)

    SECONDARY_COLOR = (165, 165, 165)
    BG_COLOR = discord.Color.from_str("#1b1d21")

    RANK_BAR_COLOR = discord.Color.blurple()

    def __init__(self, author: discord.abc.User) -> None:
        self.username_width: int = 0
        self.username_height: int = 0
        self.secondary_height: int = 0
        self.secondary_width: int = 0
        self.author: discord.abc.User = author
        self._data: utils.NASAMember | None = None
        self._avatar: bytes | None = None
        # self.canvas = Image.new(
        # "RGB", (self.WIDTH, self.HEIGHT), self.BG_COLOR.to_rgb()
        # )
        # self.draw = ImageDraw.Draw(self.canvas)

    async def async_init(self, pool: asyncpg.Pool):
        self._avatar = self.author.display_avatar.read()

        # Ranked info
        query = """
        WITH retained AS (
            SELECT * FROM levels ORDER BY level DESC, overflow_xp DESC
        ),
        ranked AS (
            SELECT *, row_number() over () AS rank FROM retained
        )
        SELECT * FROM ranked WHERE id=$1
        """

        data_f = await pool.fetchrow(query, self.author.id)

        self._data = DatabaseData(**data_f)

    @property
    def data(self) -> DatabaseData:
        if not self._data:
            raise RuntimeError("Class not initialised, please call :coro:`.async_init`")
        return self._data

    @property
    def avatar(self) -> DatabaseData:
        if not self._avatar:
            raise RuntimeError("Class not initialised, please call :coro:`.async_init`")
        return self._avatar

    # @executor_function
    def full_render(self) -> io.BytesIO:
        buffer = io.BytesIO()

    # Math functions
    def overflow_xp_to_px(self, overflow_xp: int):
        return int(
            5 * (self._data.level**2) + (50 * self._data.level) + 100 / self.WIDTH
        )

    # Image modifiers
    def add_corners(
        # slef, image: Image.Image, radius: int, top_radius: int | None = None
    ):
        """Generate round corner for image"""

    #     if top_radius is None:
    #         top_radius = radius
    #     mask = Image.new("L", image.size)
    #     draw = aggdraw.Draw(mask)
    #     brush = aggdraw.Brush("white")
    #     width, height = mask.size
    #     # upper-left corner
    #     draw.pieslice((0, 0, top_radius * 2, top_radius * 2), 90, 180, None, brush)
    #     # upper-right corner
    #     draw.pieslice(
    #         (width - top_radius * 2, 0, width, top_radius * 2), 0, 90, None, brush
    #     )
    #     # bottom-left corner
    #     draw.pieslice(
    #         (0, height - radius * 2, radius * 2, height), 180, 270, None, brush
    #     )
    #     # bottom-right corner
    #     draw.pieslice(
    #         (width - radius * 2, height - radius * 2, width, height),
    #         270,
    #         360,
    #         None,
    #         brush,
    #     )
    #     # center rectangle
    #     draw.rectangle((radius, radius, width - radius, height - radius), brush)

    #     # four edge rectangle
    #     draw.rectangle((top_radius, 0, width - top_radius, top_radius), brush)
    #     draw.rectangle((0, top_radius, top_radius, height - radius), brush)
    #     draw.rectangle((radius, height - radius, width - radius, height), brush)
    #     draw.rectangle((width - top_radius, top_radius, width, height - radius), brush)
    #     draw.flush()
    #     image = image.convert("RGBA")
    #     image.putalpha(mask)
    #     return image

    # # Image generations
    # def paste_xp_bar(self):
    #     canvas = Image.new("RGBA", (self.WIDTH, self.STATUSBAR_HEIGHT), "white")
    #     draw = ImageDraw.Draw(canvas)

    #     offset = self.WIDTH - self._data.overflow_xp


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
        if message.guild:
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

    @app_commands.command(name="rank")
    async def rank(self, inter: NASAInteraction, user: typing.Optional[discord.Member]):
        if user:
            data = user
        else:
            data = inter.user
        member = await self.bot.level_manager.fetch_user(data)
        if member:
            await inter.response.send_message(embed=member.rank_embed)
        else:
            await inter.response.send_message(content="You are not yet ranked")


async def setup(bot: NASABot):
    await bot.add_cog(Levelling(bot))
