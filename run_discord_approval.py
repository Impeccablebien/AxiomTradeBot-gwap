"""Start the Discord approval interface in review-only mode."""
import logging
from bot.notifications.discord_approval_bot import build_from_environment

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_from_environment().run_from_environment()
