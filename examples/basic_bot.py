"""
Basic example of how to use the AxiomTradingBot
"""

import asyncio
import logging
from bot.core.trading_bot import AxiomTradingBot
from bot.strategies.token_sniper import TokenSniper
from bot.strategies.wallet_tracker import WalletTracker

async def main():
    """Main function to run the bot"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize the bot with configuration
        bot = AxiomTradingBot(config_path="config/config.yaml")
        
        # Add token sniping strategy
        sniper_config = {
            'buy_amount': 0.05,      # 0.05 SOL per snipe
            'min_liquidity': 10.0,   # Minimum 10 SOL liquidity
            'max_buy_tax': 5.0,      # Maximum 5% buy tax
            'max_sell_tax': 5.0,     # Maximum 5% sell tax
            'take_profit': 100.0,    # 100% profit target
            'stop_loss': 15.0,       # 15% stop loss
            'auto_sell_delay': 60    # Auto-sell after 60 seconds
        }
        
        sniper = TokenSniper(bot, config=sniper_config)
        bot.add_strategy(sniper)
        
        # Add wallet tracking strategy
        profitable_wallets = [
            # Add profitable wallet addresses here
            # "11111111111111111111111111111112",  # Example
        ]
        
        if profitable_wallets:
            tracker_config = {
                'copy_percentage': 30.0,   # Copy 30% of their trade size
                'min_trade_size': 0.02,    # Minimum 0.02 SOL
                'max_copy_amount': 0.5,    # Maximum 0.5 SOL per copy
                'delay_seconds': 2         # 2 second delay before copying
            }
            
            tracker = WalletTracker(bot, target_wallets=profitable_wallets, config=tracker_config)
            bot.add_strategy(tracker)
        
        # Start the bot
        print("🚀 Starting AxiomTradingBot...")
        print(f"📊 Active strategies: {len(bot.strategies)}")
        print("📝 Check the logs for detailed information")
        print("🛑 Press Ctrl+C to stop the bot")
        
        await bot.start()
        
    except KeyboardInterrupt:
        print("\\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error running bot: {e}")
        logging.error(f"Bot error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
