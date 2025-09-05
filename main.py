"""
Main entry point for AxiomTradingBot
Multi-purpose trading bot for AxiomTrade API
"""

import asyncio
import argparse
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bot.core.trading_bot import AxiomTradingBot
from bot.strategies.token_sniper import TokenSniper
from bot.strategies.wallet_tracker import WalletTracker

def setup_logging(log_level: str):
    """Setup logging configuration"""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('data/bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

async def run_bot(config_path: str, strategies: list):
    """Run the trading bot with specified strategies"""
    
    try:
        # Initialize bot
        print("🤖 Initializing AxiomTradingBot...")
        bot = AxiomTradingBot(config_path=config_path)
        
        # Get bot configuration
        config = bot.config_manager.get_config()
        
        # Add strategies based on configuration and command line args
        strategies_added = 0
        
        if 'sniper' in strategies or 'all' in strategies:
            if config.sniping.enabled:
                sniper_config = bot.config_manager.get_strategy_config('TokenSniper')
                sniper = TokenSniper(bot, config=sniper_config)
                bot.add_strategy(sniper)
                strategies_added += 1
                print("🎯 Added TokenSniper strategy")
            else:
                print("⚠️  TokenSniper disabled in configuration")
        
        if 'tracker' in strategies or 'all' in strategies:
            # Check if target wallets are configured
            target_wallets = config.wallet_tracking.target_wallets if hasattr(config, 'wallet_tracking') else []
            
            if target_wallets:
                tracker_config = bot.config_manager.get_strategy_config('WalletTracker')
                tracker = WalletTracker(bot, target_wallets=target_wallets, config=tracker_config)
                bot.add_strategy(tracker)
                strategies_added += 1
                print(f"👥 Added WalletTracker strategy (tracking {len(target_wallets)} wallets)")
            else:
                print("⚠️  WalletTracker: No target wallets configured")
        
        if strategies_added == 0:
            print("❌ No strategies configured! Please check your configuration.")
            return
        
        # Display bot status
        print("\\n" + "="*60)
        print("🚀 AXIOMTRADINGBOT STARTING")
        print("="*60)
        print(f"📊 Active strategies: {strategies_added}")
        print(f"💰 Default buy amount: {config.trading.default_buy_amount} SOL")
        print(f"🎯 Take profit: {config.trading.take_profit_percentage}%")
        print(f"🛑 Stop loss: {config.trading.stop_loss_percentage}%")
        print(f"📈 Max positions: {config.trading.max_positions}")
        
        if config.notifications.discord_enabled:
            print("🔔 Discord notifications: ENABLED")
        else:
            print("🔕 Discord notifications: DISABLED")
        
        print("="*60)
        print("📝 Monitor logs for detailed activity")
        print("🛑 Press Ctrl+C to stop the bot")
        print("="*60)
        
        # Start the bot
        await bot.start()
        
    except KeyboardInterrupt:
        print("\\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error running bot: {e}")
        logging.error(f"Bot error: {e}")
        raise

def main():
    """Main function with command line argument parsing"""
    
    parser = argparse.ArgumentParser(
        description='AxiomTradingBot - Multi-purpose trading bot for AxiomTrade API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python main.py                           # Run with all strategies
  python main.py --strategies sniper       # Run only token sniper
  python main.py --strategies tracker      # Run only wallet tracker
  python main.py --strategies sniper tracker  # Run both strategies
  python main.py --config custom.yaml     # Use custom config file
  python main.py --log-level DEBUG        # Enable debug logging
        '''
    )
    
    parser.add_argument(
        '--config', 
        default='config/config.yaml',
        help='Path to configuration file (default: config/config.yaml)'
    )
    
    parser.add_argument(
        '--strategies',
        nargs='*',
        default=['all'],
        choices=['all', 'sniper', 'tracker'],
        help='Strategies to run (default: all)'
    )
    
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--setup',
        action='store_true',
        help='Run setup wizard to create configuration'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Run setup if requested
    if args.setup:
        from examples.setup_guide import main as setup_main
        setup_main()
        return
    
    # Check if config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        print("💡 Run 'python main.py --setup' to create a configuration file")
        print("💡 Or copy config/config.example.yaml to config/config.yaml")
        return
    
    # Display startup message
    print("🤖 AxiomTradingBot v1.0.0")
    print("🔗 Built for AxiomTrade API")
    print("🏗️  Community-driven open source project")
    print()
    
    # Run the bot
    try:
        asyncio.run(run_bot(args.config, args.strategies))
    except KeyboardInterrupt:
        print("\\n👋 Goodbye!")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
