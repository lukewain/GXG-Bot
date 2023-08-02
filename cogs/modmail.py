import discord
from discord import app_commands
from discord.ext import commands

import asyncio
from typing import Optional
from logging import getLogger

from src.bot import NASABot
from .errorlog import ErrorLog

log = getLogger("cogs.modmail")


class Webhook:
    def __init__(self, webhook: discord.Webhook) -> None:
        self.webhook = webhook
        self.send_lock = asyncio.Lock()
        self.channel_ids: list[int] = []

    async def send(self, *, message: discord.Message, thread: discord.Thread):
        async with self.send_lock:
            files = [
                await a.to_file()
                for a in message.attachments
                if a.size < thread.guild.filesize_limit
            ]
            try:
                await self.webhook.send(
                    content=message.content,
                    files=files,
                    username=message.author.name,
                    avatar_url=message.author.display_avatar.url,
                    thread=thread,
                )
            except discord.HTTPException as e:
                await message.add_reaction("\N{WARNING SIGN}")
                await message.author.send(
                    embed=discord.Embed(
                        description="Failed to send message. You must provide <content> or <files>, or both.",
                        color=discord.Color.red(),
                    ),
                    delete_after=5,
                )
                log.error("Could not send message", exc_info=e)
            else:
                if len(files) != len(message.attachments):
                    await message.author.send(
                        f"Failed to send {len(message.attachments) - len(files)}/{len(message.attachments)} files."
                    )


class WebhookManager:
    def __init__(self, webhooks: list[discord.Webhook]):
        self.webhooks = [Webhook(w) for w in webhooks]
        self._get_lock = asyncio.Lock()

    async def get_webhook(self, channel_id: int) -> Webhook:
        async with self._get_lock:
            webhook_list = [w for w in self.webhooks if channel_id in w.channel_ids]
            if not webhook_list:
                kps = {len(w.channel_ids): w for w in self.webhooks}
                webhook = kps[min(kps.keys())]
                webhook.channel_ids.append(channel_id)
                return webhook
            return webhook_list[0]


class ModMail(commands.Cog):
    def __init__(self, bot: NASABot):
        self.bot = bot
        self.manager: WebhookManager | None = None
        self.concurrency = commands.MaxConcurrency(
            1, per=commands.BucketType.user, wait=True
        )

    @property
    def forum(self) -> discord.ForumChannel:
        channel = self.bot.get_channel(self.bot.config.modmail_forum_id)  # type: ignore
        if not isinstance(channel, discord.ForumChannel):
            raise RuntimeError("DM Forum not found")
        return channel

    async def get_manager(self) -> WebhookManager:
        await self.bot.wait_until_ready()
        if not self.manager:
            webhooks = await self.forum.webhooks()
            self.manager = WebhookManager(webhooks)
        return self.manager

    @commands.Cog.listener("on_message")
    async def process_modmail(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.type == discord.ChannelType.private:
            await self.process_dm(message)

        if not isinstance(message.channel, discord.Thread):
            return
        if message.channel.parent == self.forum:
            await self.process_reply(message)

    async def make_thread(self, message: discord.Message) -> discord.Thread:
        thread, _ = await self.forum.create_thread(
            name=str(message.author), content=f"DM with user of ID: {message.author.id}"
        )
        await self.bot.pool.execute(
            "INSERT INTO modmail (user_id, thread_id) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET thread_id = $2",
            message.author.id,
            thread.id,
        )
        return thread

    @property
    def welcome_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Welcome to NASA's modmail!",
            description=(
                "Hello there!"
                "You have now been put in contact with NASA's moderation team!"
                "This conversation will be kept private between you and the moderation team."
                "We will reply as soon as possible"
            ),
        )

        embed.add_field(
            name="Limitations!",
            value=(
                "This will only track inital messages."
                "*Message edits, deletions and reactions are not supported yet!*"
                "For now only message content is supported!"
            ),
        )

        return embed

    async def process_dm(self, message: discord.Message):
        try:
            await self.concurrency.acquire(message)
            thread_id: Optional[int] = await self.bot.pool.fetchval(
                "SELECT thread_id FROM modmail WHERE user_id = $1", message.author.id
            )
            if not thread_id:
                await message.author.send(embed=self.welcome_embed)
                thread = await self.make_thread(message)
            else:
                thread = self.forum.get_thread(thread_id)
                if not thread:
                    try:
                        thread = await self.forum.guild.fetch_channel(thread_id)
                        if not isinstance(thread, discord.Thread):
                            thread = await self.make_thread(message)
                    except discord.HTTPException:
                        thread = await self.make_thread(message)
            manager = await self.get_manager()
            webhook = await manager.get_webhook(thread.id)
            await webhook.send(message=message, thread=thread)
        finally:
            await self.concurrency.release(message)

    async def process_reply(self, message: discord.Message):
        user_id: Optional[int] = await self.bot.pool.fetchval(
            "SELECT user_id FROM modmail WHERE thread_id=$1", message.channel.id
        )

        if not user_id:
            return
        user = await self.bot.get_or_fetch(user_id)
        try:
            if not user:
                user = await self.bot.fetch_user(user_id)

            files = [
                await a.to_file()
                for a in message.attachments
                if a.size < self.forum.guild.filesize_limit
            ]
            await user.send(
                content=f"**{discord.utils.escape_markdown(str(message.author))}:** {message.content}",
                files=files,
            )
        except discord.HTTPException as e:
            await message.add_reaction("⚠")
            await message.channel.send(f"{e.__class__.__name__}: {e}", delete_after=15)

    @commands.Cog.listener("on_user_update")
    async def mail_user_update(self, before: discord.User, after: discord.User):
        if str(before) == str(after):
            return
        thread_id: Optional[int] = await self.bot.pool.fetchval(
            "SELECT thread_id FROM modmail WHERE user_id = $1", after.id
        )
        if thread_id:
            thread = self.forum.get_thread(thread_id)
            if not thread:
                try:
                    thread = await self.forum.guild.fetch_channel(thread_id)
                    if not isinstance(thread, discord.Thread):
                        return
                except:
                    return
            if thread.archived:
                await thread.edit(archived=False)
            await thread.edit(name=str(after))


async def setup(bot: NASABot):
    await bot.add_cog(ModMail(bot))
