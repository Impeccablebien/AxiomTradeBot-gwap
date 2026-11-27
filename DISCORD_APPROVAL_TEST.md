## Discord manual approval UI (review-only test)

This is a first UI test, not a live trading integration. It posts a fictional
proposal with **ACCEPTER** and **REFUSER** buttons. Only the Discord user ID
configured as `DISCORD_OWNER_USER_ID` can decide. Decisions are kept in memory
and accepting does not call the trading engine, wallet, or AxiomTrade API.

Set these environment variables on the machine that will run the bot:

- `DISCORD_BOT_TOKEN`: Discord bot token (keep private; never commit it)
- `DISCORD_CHANNEL_ID`: ID of the Discord channel for proposals
- `DISCORD_OWNER_USER_ID`: Discord user ID allowed to decide

Install dependencies with `pip install -r requirements.txt`, then run:

```bash
python run_discord_approval.py
```

In the configured Discord channel, use `/test-proposal`. The first global
slash-command sync can take a little while to appear. The process must remain
running for the buttons to work. Do not deploy with live trading enabled.
