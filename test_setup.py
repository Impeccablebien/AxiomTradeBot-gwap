"""
Test script for AxiomTradingBot
Verifies that all components are properly installed and configured
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from bot.core.config_manager import ConfigManager
        print("✅ ConfigManager")
        
        from bot.core.database import DatabaseManager
        print("✅ DatabaseManager")
        
        from bot.core.event_manager import EventManager
        print("✅ EventManager")
        
        from bot.core.base_strategy import BaseStrategy
        print("✅ BaseStrategy")
        
        from bot.strategies.token_sniper import TokenSniper
        print("✅ TokenSniper")
        
        from bot.strategies.wallet_tracker import WalletTracker
        print("✅ WalletTracker")
        
        from bot.risk_management.risk_manager import RiskManager
        print("✅ RiskManager")
        
        from bot.notifications.notification_manager import NotificationManager
        print("✅ NotificationManager")
        
        from bot.notifications.discord_notifier import DiscordNotifier
        print("✅ DiscordNotifier")
        
        from bot.core.trading_bot import AxiomTradingBot
        print("✅ AxiomTradingBot")
        
        print("\\n✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Test configuration management"""
    print("\\n🔧 Testing configuration...")
    
    try:
        from bot.core.config_manager import ConfigManager
        
        # Test with non-existent config (should use defaults)
        config_manager = ConfigManager("nonexistent.yaml")
        config = config_manager.get_config()
        
        print(f"✅ Default buy amount: {config.trading.default_buy_amount}")
        print(f"✅ Take profit: {config.trading.take_profit_percentage}%")
        print(f"✅ Stop loss: {config.trading.stop_loss_percentage}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False

def test_database():
    """Test database functionality"""
    print("\\n💾 Testing database...")
    
    try:
        from bot.core.database import DatabaseManager
        
        # Create test database
        db = DatabaseManager("data/test.db")
        print("✅ Database initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

async def test_event_manager():
    """Test event manager"""
    print("\\n📡 Testing event manager...")
    
    try:
        from bot.core.event_manager import EventManager, EventType
        
        event_manager = EventManager()
        await event_manager.start()
        
        # Test event publishing
        await event_manager.publish(EventType.BOT_STARTED, {}, "test")
        print("✅ Event published")
        
        await event_manager.stop()
        print("✅ Event manager stopped")
        
        return True
        
    except Exception as e:
        print(f"❌ Event manager error: {e}")
        return False

def test_axiom_api():
    """Test AxiomTrade API connection (basic)"""
    print("\\n🔗 Testing AxiomTrade API...")
    
    try:
        from axiomtradeapi import AxiomTradeClient
        
        # Just test that we can create a client (without login)
        client = AxiomTradeClient()
        print("✅ AxiomTrade client created")
        
        return True
        
    except Exception as e:
        print(f"❌ AxiomTrade API error: {e}")
        return False

async def run_tests():
    """Run all tests"""
    print("🧪 Running AxiomTradingBot Tests")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Database", test_database),
        ("Event Manager", test_event_manager),
        ("AxiomTrade API", test_axiom_api)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
    
    print("\\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The bot is ready to use.")
        print("\\n📝 Next steps:")
        print("1. Copy config/config.example.yaml to config/config.yaml")
        print("2. Edit config.yaml with your AxiomTrade credentials")
        print("3. Run: python main.py --setup (for guided setup)")
        print("4. Or run: python main.py (to start the bot)")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print("💡 Make sure all dependencies are installed: pip install -r requirements.txt")
    
    return passed == total

def main():
    """Main test function"""
    try:
        asyncio.run(run_tests())
    except KeyboardInterrupt:
        print("\\n🛑 Tests interrupted")
    except Exception as e:
        print(f"💥 Test runner error: {e}")

if __name__ == "__main__":
    main()
