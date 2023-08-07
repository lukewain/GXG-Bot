import discord
from discord import app_commands
from discord.ext import commands

from dataclasses import dataclass
from logging import getLogger

import src

logger = getLogger("NASA.voicechannels")


@dataclass
class VoiceChannel:
    channel_id: int
    owner: int
    owner_in: bool
    limit: int

    @property
    def get_limit(self) -> str:
        return "No limit" if self.limit == 0 else str(self.limit)


class VoiceHandler:
    def __init__(self, bot: src.NASABot):
        self.bot = bot

    async def start(self):
        self.channel_cache: dict[int, VoiceChannel] = {}

    def add_handler(self, voicestate: VoiceChannel):
        self.channel_cache[voicestate.channel_id] = voicestate

    def get_handler(self, channel_id: int) -> VoiceChannel:
        try:
            return self.channel_cache[channel_id]
        except KeyError:
            ...

    def update_handler(self, voicestate: VoiceChannel):
        self.channel_cache[voicestate.channel_id] = voicestate

    async def get_owner(self, channel_id: int) -> discord.Member | discord.User:
        voicestate = self.channel_cache[channel_id]

        member = await self.bot.get_or_fetch(voicestate.owner)

        return member

    def already_has(self, owner_id: int) -> int | None:
        for c in self.channel_cache.values():
            if c.owner == owner_id:
                return c.channel_id

    def __repr__(self):
        return f"<Voice handler with {len(self.channel_cache)} active voice channel{'s' if len(self.channel_cache) > 1 or len(self.channel_cache) == 0 else ''}>"


class Voices(commands.Cog):
    def __init__(self, bot: src.NASABot):
        self.bot = bot
        self.voice_handler = VoiceHandler(bot)

    async def cog_load(self):
        if self.bot.config.join_to_create_ids is None:
            logger.error(
                "There are no join to create channels, add voice channels for this to work"
            )

        await self.voice_handler.start()
        # await self.bot.unload_extension("cogs.voices")

    async def verify_join_channels(self):
        ...
        # TODO: Write logic to verify if the Join to create channels still exist

    @commands.Cog.listener("on_voice_state_update")
    async def handle_voice_change(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if self.bot.config.join_to_create_ids is None:
            return
        elif before.channel is None and after.channel is None:
            return

        elif (
            after.channel is not None
            and after.channel.id in self.bot.config.join_to_create_ids
        ):
            logger.info(f"{member} joined <join_to_create>")
            already_exists = self.voice_handler.already_has(member.id)
            if already_exists is not None:
                logger.info(f"{member} already has a channel!")
                c = await self.bot.get_or_fetch_channel(already_exists)
                return await member.move_to(c)
            plural = "'" if member.name.endswith("s") else "'s"
            new_vc = await after.channel.category.create_voice_channel(
                name=f"{member.name}{plural} Channel"
            )

            new_vc_entry = VoiceChannel(new_vc.id, member.id, True, 0)

            self.voice_handler.add_handler(new_vc_entry)

            await member.move_to(new_vc)

        elif (
            before.channel is not None
            and len(before.channel.members) == 0
            and before.channel.id not in self.bot.config.join_to_create_ids
            and before.channel.id in self.voice_handler.channel_cache.keys()
        ):
            logger.warn(f"{before.channel.name} is empty, deleting!")
            self.voice_handler.channel_cache.pop(before.channel.id)
            logger.warn(
                f"There are now {len(self.voice_handler.channel_cache)} channel{'s' if len(self.voice_handler.channel_cache) > 1 or len(self.voice_handler.channel_cache) == 0 else ''}"
            )
            await before.channel.delete()

        elif before.channel is not None and len(before.channel.members) > 0:
            voicestate = self.voice_handler.get_handler(before.channel.id)

            if member.id == voicestate.owner and after.channel is None:
                voicestate.owner_in = False
                self.voice_handler.update_handler(voicestate)

            member = self.bot.get_user(voicestate.owner)
            if not member:
                member = self.bot.fetch_user(voicestate.owner)

    @app_commands.command(name="create-voice")
    @app_commands.default_permissions(administrator=True)
    async def create_join_vc_channel(
        self, inter: src.NASAInteraction, category: discord.CategoryChannel
    ):
        voice = await category.create_voice_channel(name="Join to create", user_limit=1)
        await inter.response.send_message(f"Created {voice.mention}")

        # Update the config to have the voice channel id in the list

        self.bot.config.update_join_to_create(voice.id)
        logger.info("Updated join_to_create_ids")

    @commands.command(name="listvoice", aliases=["lv"])
    @commands.is_owner()
    async def listvoices(self, ctx: src.NASAContext):
        await ctx.reply(self.voice_handler)


async def setup(bot: src.NASABot):
    await bot.add_cog(Voices(bot))
