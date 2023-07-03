from email import message
import discord
from discord.ext import commands
from discord import app_commands

import traceback
import logging

from src.bot import GXGBot, GXGContext
from .errorlog import ErrorLog

_logger = logging.getLogger("ErrorHandler")


class ErrorHandler(commands.Cog):
    def __init__(self, bot: GXGBot):
        self.bot = bot

    async def cog_load(self):
        self._default_tree_error = self.bot.tree.on_error
        self.bot.tree.on_error = self.on_app_command_error

    async def cog_unload(self):
        self.bot.tree.on_error = self._default_tree_error

    async def on_app_command_error(
        self,
        interaction: discord.Interaction[GXGBot],
        error: app_commands.AppCommandError,
    ):
        if isinstance(error, app_commands.CommandOnCooldown):
            if interaction.response.is_done():
                return await interaction.followup.send(
                    f"You must wait another {error.retry_after:.1f} seconds!"
                )
            return await interaction.response.send_message(
                f"You must wait another {error.retry_after:.1f} seconds!"
            )

        else:
            trace: str = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            errorlog = await ErrorLog.create(
                interaction.client.pool,
                traceback=trace,
                item=f"Command: {interaction.command.name if interaction.command else '<Name not found>'}",
            )

            _logger.error(f"Ignoring exception in app command {interaction.command}")
            _logger.error(trace)

            try:
                if interaction.response.is_done():
                    msg = await interaction.followup.send(
                        embed=errorlog.pub_embed, wait=True
                    )
                    _logger.error(
                        f"Notification message successfully sent in {interaction.channel.id=} {msg.id=}"  # type: ignore will always have an id
                    )
                else:
                    await interaction.response.send_message(embed=errorlog.pub_embed)
            except (discord.Forbidden, discord.HTTPException):
                _logger.error(
                    f"Could not send error notification in {interaction.channel.id=}"  # type: ignore will always have an id
                )

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: GXGContext, error: commands.CommandError
    ) -> None:
        # testing leaving this off
        # if hasattr(ctx.command, 'on_error'):
        #     return

        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return

        ignored = (
            commands.CommandNotFound,
            commands.NotOwner,
            commands.TooManyArguments,
        )

        error = getattr(error, "original", error)

        if isinstance(error, ignored):
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.send(f"{ctx.command} has been disabled.", ephemeral=True)

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send(  # type: ignore   It works okay.
                    f"{ctx.command} can not be used in Private Messages.",
                    ephemeral=True,
                )
            except discord.HTTPException:
                pass

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"A little too quick there. Try again in {error.retry_after:,.1f} seconds.",
                delete_after=4.0,
                ephemeral=True,
            )

        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(
                f"You do not have permission to use that command.", ephemeral=True
            )

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"You must have missed an argument ({error.param.name}), please try again.",
                ephemeral=True,
                delete_after=30.0,
            )

        elif isinstance(error, commands.BotMissingPermissions):
            try:
                perm_strings = [
                    perm.replace("_", " ").title() for perm in error.missing_permissions
                ]
                await ctx.send(
                    f"I am missing the permissions needed to run that command: {', '.join(perm_strings)}"
                )
            except discord.Forbidden:
                _logger.info(
                    f"Missing permissions {', '.join(perm_strings)} to run command '{ctx.command.qualified_name}' in channel_id={ctx.channel.id}"  # type: ignore perm_strings won't be unbound due to specific error
                )

        elif isinstance(error, commands.UserNotFound):
            await ctx.send(f"Could not find user {error.argument}.")

        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"You provided an invalid argument.")

        elif isinstance(error, commands.BadLiteralArgument):
            await ctx.send(
                f"Invalid literal given, valid options: {' '.join(error.literals)}"
            )

        elif isinstance(error, commands.RangeError):
            await ctx.send(f"Invalid value (**{error.value}**) given.")

        elif isinstance(error, commands.BadUnionArgument):
            await ctx.send(f"Failed converting {error.param.name}")

        else:
            trace = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            errorlog = await ErrorLog.create(
                ctx.bot.pool, traceback=trace, item=f"Command: {ctx.command.name}"  # type: ignore will always have a name
            )

            _logger.error("Ignoring exception in command {}:".format(ctx.command))
            _logger.error(trace)

            try:
                msg = await ctx.channel.send(embed=errorlog.pub_embed)
                _logger.error(
                    f"Notification message succesfully sent in {ctx.channel.id=} {msg.id=}"
                )
            except (discord.Forbidden, discord.HTTPException):
                _logger.error(f"Could not send error notification in {ctx.channel.id=}")


async def setup(bot: GXGBot):
    _logger.info("Loading cog ErrorHandler")
    await bot.add_cog(ErrorHandler(bot))
