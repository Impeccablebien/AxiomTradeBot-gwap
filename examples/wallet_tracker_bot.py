"""
Wallet Tracking example for AxiomTradingBot
Focuses on copying trades from profitable wallets
"""

import asyncio
import logging
from bot.core.trading_bot import AxiomTradingBot
from bot.strategies.wallet_tracker import WalletTracker

async def main():
    """Run a wallet tracking bot"""
    
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Initialize bot
        bot = AxiomTradingBot(config_path="config/config.yaml")
        
        # List of profitable wallets to track
        # Replace these with actual profitable wallet addresses
        target_wallets = [
            # "11111111111111111111111111111112",  # Example System Program
            # "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # Example Token Program
            # Add your researched profitable wallets here
        ]
        
        if not target_wallets:
            print("❌ No target wallets configured!")
            print("📝 Please add profitable wallet addresses to the target_wallets list")
            print("🔍 Research profitable wallets and add their addresses")
            return
        
        # Conservative copy trading configuration
        tracker_config = {
            'copy_percentage': 25.0,     # Copy 25% of their position size
            'min_trade_size': 0.05,      # Only copy trades >= 0.05 SOL
            'max_copy_amount': 1.0,      # Never copy more than 1 SOL
            'take_profit': 80.0,         # 80% profit target
            'stop_loss': 25.0,           # 25% stop loss
            'delay_seconds': 3,          # 3-second delay to avoid front-running
            'blacklisted_tokens': [
                # Add tokens you don't want to copy
            ]
        }
        
        tracker = WalletTracker(bot, target_wallets=target_wallets, config=tracker_config)
        bot.add_strategy(tracker)
        
        print("👥 Starting Wallet Tracker...")
        print(f"🎯 Tracking {len(target_wallets)} wallets")
        print(f"📊 Copy percentage: {tracker_config['copy_percentage']}%")
        print(f"💰 Min trade size: {tracker_config['min_trade_size']} SOL")
        print(f"🎯 Take profit: {tracker_config['take_profit']}%")
        print(f"⏰ Copy delay: {tracker_config['delay_seconds']}s")
        
        # Display tracked wallets
        for i, wallet in enumerate(target_wallets, 1):
            print(f"📍 Wallet {i}: {wallet[:8]}...{wallet[-8:]}")
        
        await bot.start()
        
    except KeyboardInterrupt:
        print("\\n🛑 Wallet tracker stopped")
    except Exception as e:
        print(f"❌ Tracker error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
