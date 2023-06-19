import datetime
import os
from humanreadable import Time  # type: ignore
import discord
from discord import User, app_commands
from discord.ext import commands

from typing import Self

# from src.bot import GXGBot, GXGInteraction
from .. import utils


class Moderation(commands.Cog):
    def __init__(self: Self, bot: GXGBot):
        self.bot = bot

    async def unmute_autocomplete(self, interaction: GXGInteraction, current: str):
        muted_members = await interaction.pool.fetch(
            "SELECT * FROM muted WHERE expired = False"
        )

    @app_commands.command(name="mute", description="Allows you to mute a user")  # type: ignore
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def mute(
        self,
        interaction: GXGInteraction,
        user: discord.Member,
        reason: str | None,
        duration: str,
    ):
        """
        |coro|

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
        role = interaction.guild.get_role(int(os.environ["MUTE_ROLE_ID"]))  # type: ignore  Guild will never be None

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
        interaction: GXGInteraction,
        member: discord.Member,
        reason: app_commands.Range[str, 15, 300],
    ):
        """
        |coro|

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

        res = await interaction.pool.fetchrow(
            "SELECT * FROM warnings WHERE id=$1", member.id
        )

        if not res:
            await interaction.pool.execute(
                "INSERT INTO warnings (id, infractions, infraction_reasons, removed_infractions) VALUES ($1, $2, $3, $4)",
                member.id,
                1,
                [reason],
                0,
            )
            infractions = 1

        else:
            infractions = await interaction.pool.fetchval(
                "UPDATE warnings SET infractions = infractions + 1, infraction_reasons = array_append(infraction_reasons, $1) WHERE id=$2",
                reason,
                member.id,
            )

        log_embed = discord.Embed(color=discord.Color.red())
        log_embed.set_author(
            name=member.name, url=member.avatar.url if member.avatar else None
        )
        pub_embed = log_embed.copy()
        pub_embed.add_field(name="Reason", value=reason)

        vals = {
            "Reason": reason,
            "Total Infractions": infractions,
            "Moderator": f"{interaction.user} (ID: {interaction.user.id})",
        }

        for k, v in vals:
            log_embed.add_field(name=k, value=v, inline=False)

        log_channel: discord.TextChannel | None = self.bot.get_channel(  # type: ignore
            interaction.client.config.log_channel_id
        )
        if not log_channel:
            log_channel: discord.TextChannel | None = await self.bot.fetch_channel(  # type: ignore
                interaction.client.config.log_channel_id
            )

        await log_channel.send(embed=log_embed)
        await interaction.response.send_message(embed=pub_embed)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
