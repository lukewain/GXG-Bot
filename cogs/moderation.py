import datetime
import os
import asyncpg
from humanreadable import Time  # type: ignore
import discord
from discord import app_commands
from discord.ext import commands

from typing import Self
import re

from src.bot import NASABot, NASAInteraction
import utils


class Moderation(commands.Cog):
    def __init__(self: Self, bot: NASABot):
        self.bot = bot
        self.url_regex = re.compile(
            r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?"
        )

    async def unmute_autocomplete(self, interaction: NASAInteraction, current: str):
        muted_members = await self.bot.pool.fetch(
            "SELECT * FROM muted WHERE expired = False"
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id in self.bot.immune:
            return
        check = self.url_regex.match(message.content)

        if check is None:
            pass

        else:
            await utils.ModerationLog.add_moderation_action(
                self.bot.pool,
                self.bot.user.id,  # type: ignore will always have a value as this will only be used when the bot is logged in
                "Warn",
                "Sending invite links",
                message.author.id,
            )

            await message.delete()

    @app_commands.command(name="mute", description="Allows you to mute a user")  # type: ignore
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def mute(
        self,
        interaction: NASAInteraction,
        user: discord.Member,
        reason: str | None,
        duration: str,
    ):
        """
        This is a command that is used to mute members

        Parameters
        ----------
        user: `discord.Member`
            The user to mute
        reason: `Optional[str]`
            The reason the user is being muted. Can be left blank
        duration: `str`
            The duration of the mute, can be set to indefinite to unmute manually (e.g. 10 minutes)
        """

        if user.id in self.bot.immune:
            embed = discord.Embed(description="You cannot mute this user!")
            embed.set_author(name=user.global_name, url=user.display_avatar.url)
            return await interaction.response.send_message(embed=embed)

        if reason is None:
            reason = "No reason provided."

        reason += f" | {interaction.user} (ID: {interaction.user.id})"

        seconds = Time(duration).seconds

        timeout_until = datetime.timedelta(seconds=seconds)
        await user.timeout(timeout_until, reason=reason)
        role = interaction.guild.get_role(int(self.bot.config.mute_role_id))  # type: ignore  Guild will never be None

        await user.add_roles(role)  # type: ignore   Error handler will handle this one chief

        embed = discord.Embed(
            description=f"{user} has been timed out {'for ' if duration != -1 else ''}{duration if duration != -1 else 'indefinitely'}"
        )
        embed.set_author(name=user.global_name, url=user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="warn")  # type: ignore
    @app_commands.default_permissions(moderate_members=True)
    async def warn(
        self,
        interaction: NASAInteraction,
        member: discord.Member,
        reason: app_commands.Range[str, 15, 300],
    ):
        """
        A command used to warn members

        Parameters
        ----------
        member: `discord.Member`
            The member you would like to warn
        reason: `str`
            The reason you are warning them
        """

        """
        TODO:
            Check if user already has a warnings profile
                - If they do add warning
                - If not, create a profile with one warning already
            Check number of warnings user has. If greater than threshold. Alert moderator(s)
        """

        warning: utils.Warning = await utils.Warning.add(
            self.bot.pool, member.id, reason
        )

        log_embed = discord.Embed(color=discord.Color.red())
        log_embed.set_author(
            name=member.name, url=member.avatar.url if member.avatar else None
        )
        pub_embed = log_embed.copy()
        pub_embed.add_field(name="Reason", value=reason)

        vals = {
            "Reason": reason,
            "Total Infractions": warning.total_warnings,
            "Moderator": f"{interaction.user} (ID: {interaction.user.id})",
        }

        for k, v in vals:
            log_embed.add_field(name=k, value=v, inline=False)

        if self.bot.config.log_webhook_url:
            log_webhook = discord.Webhook.from_url(url=self.bot.config.log_webhook_url)
            await log_webhook.send(embed=log_embed)
            # type: ignore will be raised by error handler if log_channel is None
        await interaction.response.send_message(embed=pub_embed)

    @app_commands.command(name="infractions")  # type: ignore
    @app_commands.default_permissions(moderate_members=True)
    async def infractions(self, interaction: NASAInteraction, user: discord.Member):
        """
        A command to view a users infractions

        Paramters
        ---------
        user : `discord.Member`
            The user who's infractions you want to view
        """

        if user.id in self.bot.immune:
            embed = discord.Embed(
                title="Infractions",
                description="This user is immune to all moderation actions.",
                color=discord.Color.orange(),
            )
            return await interaction.response.send_message(embed=embed)

        # Fetch all the user infractions
        # This will be done using the moderation log

        logs: list[
            utils.ModerationLog
        ] | None = await utils.ModerationLog.get_moderatee_logs(self.bot.pool, user.id)

        if not logs:
            embed = discord.Embed(
                title=f"{user}'s Infractions",
                description="This user has no infractions.",
                color=discord.Color.orange(),
            )
            return await interaction.response.send_message(embed=embed)

        await interaction.response.defer(thinking=True)

        pag = utils.Paginator()

        for action in logs:
            moderator = self.bot.get_user(action.moderator_id)
            pag.add_line(
                f"Infraction ID: {action.entry_id}\nModerator: {moderator}({action.moderator_id})\nReason: {action.reason}\nOn: <t:{action.unixtimestamp}:R>"
            )

        embed = discord.Embed(
            title=f"{user.mention}'s Infractions", colour=discord.Color.orange()
        )

        v = utils.PaginatorView(pag, interaction.user, embed=embed)

        await interaction.followup.send(view=v, embed=embed)

    config = app_commands.Group(
        name="config",
        description="Commands that you can use to configure the bot",
        guild_only=True,
    )

    @config.command(name="log-channel")  # type: ignore
    async def set_log_channel(
        self, interaction: NASAInteraction, channel: discord.TextChannel
    ):
        """
        A command used to set the log channel

        Parameters
        ----------

        channel: `discord.TextChannel`
            The channel to create the webhook in
        """
        if self.bot.config.log_webhook_url:
            embed = discord.Embed(
                title="This will overwrite the current channel!",
                description="Are you sure you want to do this?",
            )
            view = utils.ConfirmationView()
            await interaction.response.send_message(view=view)
            await view.wait()

            if view.value is None:
                await interaction.response.edit_message(
                    content="This view timed out.", view=None
                )
            elif view.value:
                self.log_webhook = await channel.create_webhook(name="NASA-Logging")
                self.bot.config._update_value("log_webhook_url", self.log_webhook.url)
                await interaction.response.edit_message(
                    content="You have updated the `Log Channel ID`!", view=None
                )
            else:
                await interaction.response.edit_message(
                    content="The `Log Channel ID` had not been updated!", view=None
                )

        self.log_webhook = await channel.create_webhook(name="NASA-Logging")
        self.bot.config._update_value("log_webhook_url", self.log_webhook.url)

    @config.command(name="modmail-channel")  # type: ignore
    async def set_modmail_channel(
        self, interaction: NASAInteraction, channel: discord.ForumChannel
    ):
        """
        A command used to set the log channel

        Parameters
        ----------

        channel: `discord.ForumChannel`
            The channel to create the new modmail's in
        """
        if self.bot.config.modmail_forum_id:
            embed = discord.Embed(
                title="This will overwrite the current channel!",
                description="Are you sure you want to do this?",
            )
            view = utils.ConfirmationView()
            await interaction.response.send_message(view=view, embed=embed)
            await view.wait()

            if view.value is None:
                await interaction.response.edit_message(
                    content="This view timed out.", view=None
                )

            elif view.value:
                self.bot.config._update_value("mailmod_forum_id", channel.id)
                await interaction.response.edit_message(
                    content="You have updated the `MailMod Forum ID`!", view=None
                )
            else:
                await interaction.response.edit_message(
                    content="The `MailMod Forum ID` had not been updated!", view=None
                )

        self.bot.config._update_value("mailmod_forum_id", channel.id)
        await interaction.response.send_message("You have set the `MailMod Forum ID`!")


class Logging(commands.Cog):
    def __init__(self, bot: NASABot):
        self.bot = bot

    # Listeners
    # ---------------------------

    @commands.Cog.listener("on_raw_message_delete")
    async def deleted_message_logging(self, message: discord.Message):
        ...

    @commands.Cog.listener("on_raw_message_edit")
    async def edited_message_logging(
        self, before: discord.Message, after: discord.Message
    ):
        ...

    @commands.Cog.listener("on_member_remove")
    async def removed_member_logging(self, member: discord.Member):
        ...

    @commands.Cog.listener("on_member_join")
    async def joined_member_logging(self, member: discord.Member):
        ...

    @commands.Cog.listener("on_member_ban")
    async def banned_member_logging(self, member: discord.Member):
        ...

    @commands.Cog.listener("on_member_update")
    async def updated_member_logging(
        self, before: discord.Member, after: discord.Member
    ):
        ...

    # Commands
    # ---------------------------

    @app_commands.command(name="set-log")
    @app_commands.default_permissions(administrator=True)
    async def set_log_channel(
        self, inter: NASAInteraction, channel: discord.TextChannel
    ):
        if self.bot.config.log_channel_id is not None:
            view = utils.ConfirmationView()
            await inter.response.send_message(
                embed=discord.Embed(
                    title="Log Channel Conflict!",
                    description="There is already a log channel set, would you like to override it?",
                ),
                view=view,
                ephemeral=True,
            )
            await view.wait()

            if view.value is None:
                await inter.response.edit_message(
                    view=None, content="This view timed out."
                )
        ...


async def setup(bot):
    await bot.add_cog(Moderation(bot))
