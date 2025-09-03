"""
Token Sniping example for AxiomTradingBot
Focuses specifically on token sniping with aggressive settings
"""

import asyncio
import logging
from bot.core.trading_bot import AxiomTradingBot
from bot.strategies.token_sniper import TokenSniper

async def main():
    """Run an aggressive token sniping bot"""
    
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Initialize bot
        bot = AxiomTradingBot(config_path="config/config.yaml")
        
        # Aggressive sniping configuration
        sniper_config = {
            'buy_amount': 0.1,           # Higher buy amount
            'min_liquidity': 5.0,        # Lower liquidity requirement
            'max_buy_tax': 15.0,         # Higher tax tolerance
            'max_sell_tax': 15.0,        # Higher tax tolerance
            'take_profit': 200.0,        # 200% profit target
            'stop_loss': 30.0,           # 30% stop loss
            'auto_sell_delay': 30,       # Quick 30-second auto-sell
            'max_positions': 3,          # Limit concurrent positions
            'blacklisted_tokens': [
                # Add known honeypot or scam tokens here
            ]
        }
        
        sniper = TokenSniper(bot, config=sniper_config)
        bot.add_strategy(sniper)
        
        print("🎯 Starting Aggressive Token Sniper...")
        print("⚠️  WARNING: Aggressive settings - higher risk!")
        print(f"💰 Buy amount: {sniper_config['buy_amount']} SOL")
        print(f"🎯 Take profit: {sniper_config['take_profit']}%")
        print(f"🛑 Stop loss: {sniper_config['stop_loss']}%")
        print(f"⏰ Auto-sell: {sniper_config['auto_sell_delay']}s")
        
        await bot.start()
        
    except KeyboardInterrupt:
        print("\\n🛑 Sniper stopped")
    except Exception as e:
        print(f"❌ Sniper error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
