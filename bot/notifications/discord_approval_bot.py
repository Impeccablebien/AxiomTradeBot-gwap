"""Discord approval UI for AxiomTradeBot.

This module is deliberately review-only: accepting a proposal records approval
in memory and NEVER calls the trading engine or signs/submits a transaction.
"""
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict
from uuid import uuid4

import discord
from discord import app_commands

logger = logging.getLogger("DiscordApprovalBot")


@dataclass
class Proposal:
    proposal_id: str
    action: str
    token_address: str
    amount: float
    reason: str
    created_at: datetime
    status: str = "PENDING"


class ApprovalView(discord.ui.View):
    def __init__(self, bot: "DiscordApprovalBot", proposal: Proposal):
        super().__init__(timeout=300)
        self.bot = bot
        self.proposal = proposal

    async def _decide(self, interaction: discord.Interaction, decision: str):
        if interaction.user.id != self.bot.owner_user_id:
            await interaction.response.send_message(
                "⛔ Seul le propriétaire configuré peut répondre à cette proposition.",
                ephemeral=True,
            )
            return

        current = self.bot.proposals.get(self.proposal.proposal_id)
        if current is None or current.status != "PENDING":
            await interaction.response.send_message(
                "Cette proposition n'est plus en attente.", ephemeral=True
            )
            return

        current.status = decision
        for child in self.children:
            child.disabled = True

        if decision == "APPROVED":
            message = (
                "✅ Proposition approuvée manuellement. "
                "Aucun achat/vente n'a été exécuté : le trading reste verrouillé."
            )
        else:
            message = "❌ Proposition refusée. Aucune transaction n'a été exécutée."

        await interaction.response.edit_message(
            content=f"{self.message_content()}\n\n**Décision : {message}**",
            view=self,
        )

    def message_content(self) -> str:
        p = self.proposal
        return (
            f"🧪 **Proposition de trade — mode test uniquement**\n"
            f"Action : **{p.action.upper()}**\n"
            f"Token : `{p.token_address}`\n"
            f"Montant proposé : **{p.amount:g} SOL**\n"
            f"Motif : {p.reason or 'Non précisé'}\n"
            f"ID : `{p.proposal_id}`"
        )

    @discord.ui.button(label="ACCEPTER", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._decide(interaction, "APPROVED")

    @discord.ui.button(label="REFUSER", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._decide(interaction, "REJECTED")


class DiscordApprovalBot(discord.Client):
    def __init__(self, token: str, channel_id: int, owner_user_id: int):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.token_value = token
        self.channel_id = channel_id
        self.owner_user_id = owner_user_id
        self.tree = app_commands.CommandTree(self)
        self.proposals: Dict[str, Proposal] = {}

        @self.tree.command(
            name="test-proposal",
            description="Publie une proposition fictive pour tester les boutons",
        )
        async def test_proposal(interaction: discord.Interaction):
            if interaction.user.id != self.owner_user_id:
                await interaction.response.send_message(
                    "⛔ Commande réservée au propriétaire.", ephemeral=True
                )
                return
            if interaction.channel_id != self.channel_id:
                await interaction.response.send_message(
                    "Utilise cette commande dans le salon Discord configuré.",
                    ephemeral=True,
                )
                return

            proposal = Proposal(
                proposal_id=uuid4().hex[:12],
                action="buy",
                token_address="DEMO_TOKEN_ADDRESS",
                amount=0.01,
                reason="Proposition fictive pour vérifier les boutons Discord.",
                created_at=datetime.now(timezone.utc),
            )
            self.proposals[proposal.proposal_id] = proposal
            view = ApprovalView(self, proposal)
            await interaction.response.send_message(view.message_content(), view=view)

    async def setup_hook(self):
        await self.tree.sync()
        logger.info("Commandes Discord synchronisées.")

    async def on_ready(self):
        logger.info("Connecté à Discord en tant que %s", self.user)

    def run_from_environment(self):
        self.run(self.token_value, log_handler=None)


def build_from_environment() -> DiscordApprovalBot:
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    channel = os.getenv("DISCORD_CHANNEL_ID", "").strip()
    owner = os.getenv("DISCORD_OWNER_USER_ID", "").strip()
    if not token or not channel or not owner:
        raise RuntimeError(
            "Variables requises : DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID, "
            "DISCORD_OWNER_USER_ID."
        )
    return DiscordApprovalBot(token, int(channel), int(owner))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_from_environment().run_from_environment()
