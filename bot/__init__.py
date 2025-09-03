"""
AxiomTradeBot - Core Package
Multi-purpose trading bot for AxiomTrade API
"""

__version__ = "1.0.0"
__author__ = "AxiomTrade Community"
__license__ = "MIT"

from .core.trading_bot import AxiomTradingBot
from .core.base_strategy import BaseStrategy
from .strategies.token_sniper import TokenSniper
from .strategies.wallet_tracker import WalletTracker

__all__ = [
    "AxiomTradingBot",
    "BaseStrategy", 
    "TokenSniper",
    "WalletTracker"
]
