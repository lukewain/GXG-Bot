from __future__ import annotations

import discord
from discord.ui import View, button, Button

from datetime import datetime, timedelta
from typing import Self, reveal_type, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from src.bot import NASABot, NASAInteraction

__all__ = ("ConfirmationView",)


class ConfirmationView(View):
    def __init__(self: Self):
        super().__init__(timeout=60)
        self.value = None

    @button(label="Confirm", style=discord.ButtonStyle.green)
    async def _confirm_callback(self, interaction: discord.Interaction, button: Button):
        self.value = True
        self.stop()

    @button(label="Deny", style=discord.ButtonStyle.red)
    async def _deny_callback(self, interaction: discord.Interaction, button: Button):
        self.value = False
        self.stop()


class PersistentLFGView(View):
    def __init__(self: Self):
        super().__init__(timeout=None)

    @button(label="Unrated", style=discord.ButtonStyle.green)
    async def unrated_lfg(self, interaction: discord.Interaction, button: Button):
        ...

    @button(label="Competetive", style=discord.ButtonStyle.red)
    async def competitive_lfg(self, interaction: discord.Interaction, button: Button):
        ...

    @button(label="Other", style=discord.ButtonStyle.blurple)
    async def other_lfg(self, interaction: discord.Interaction, button: Button):
        ...


class UnratedMemberSelect(discord.ui.Select):
    def __init__(self, author: Union[discord.User, discord.Member]):
        options = [
            discord.SelectOption(label="2"),
            discord.SelectOption(label="3"),
            discord.SelectOption(label="4"),
            discord.SelectOption(label="5"),
        ]

        self.author = author

        super().__init__(
            placeholder="Select the number of players you require",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def interaction_check(self, interaction: discord.Interaction):
        return self.author.id == interaction.user.id

    async def callback(self, interaction: NASAInteraction):
        query = "INSERT INTO lfg (author_id, gamemode, players, player_limit, expires_at) VALUES ($1, $2, $3, $4, $5)"

        timeout = datetime.now() + timedelta(minutes=10)

        await interaction.client.pool.execute(
            query, interaction.user.id, [], self.values[0], round(timeout.timestamp())
        )
        
        
