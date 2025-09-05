"""
Main Trading Bot Class for AxiomTradingBot
Coordinates all strategies, monitoring, and trading execution
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Core imports
from .base_strategy import BaseStrategy, TradeSignal, Position
from .config_manager import ConfigManager
from .database import DatabaseManager, TradeRecord, PositionRecord
from .event_manager import EventManager, EventType

# AxiomTrade API
from axiomtradeapi import AxiomTradeClient

# Strategy imports
try:
    from ..risk_management.risk_manager import RiskManager
    from ..notifications.notification_manager import NotificationManager
except ImportError:
    # Fallback imports for development
    class RiskManager:
        def __init__(self, config):
            self.config = config
        async def can_execute_trade(self, signal):
            return True
    
    class NotificationManager:
        def __init__(self, config):
            self.config = config
        async def start(self):
            pass
        async def stop(self):
            pass
        async def send_bot_notification(self, title, message, level):
            pass
        async def send_trade_notification(self, signal, success, tx_hash):
            pass
        async def send_risk_notification(self, title, message, level):
            pass
        async def send_error_notification(self, message, details):
            pass

class AxiomTradingBot:
    """
    Main trading bot that coordinates all components
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the trading bot
        
        Args:
            config_path: Path to configuration file
        """
        # Initialize logging first
        self._setup_logging()
        self.logger = logging.getLogger("AxiomTradingBot")
        self.logger.info("Initializing AxiomTradingBot...")
        
        # Core components
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()
        
        # Validate configuration
        if not self.config_manager.validate_config():
            raise ValueError("Invalid configuration. Please check your config file.")
        
        self.database = DatabaseManager()
        self.event_manager = EventManager()
        self.risk_manager = RiskManager(self.config.risk_management)
        self.notification_manager = NotificationManager(self.config.notifications)
        
        # AxiomTrade API client
        self.api_client = AxiomTradeClient(
            username=self.config.axiom_trade.email,
            password=self.config.axiom_trade.password
        )
        
        # Bot state
        self.strategies: Dict[str, BaseStrategy] = {}
        self.is_running = False
        self.is_paused = False
        self.start_time = None
        
        # Performance tracking
        self.total_trades = 0
        self.total_pnl = 0.0
        self.daily_pnl = 0.0
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        self.logger.info("AxiomTradingBot initialized successfully")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('data/bot.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            asyncio.create_task(self.stop())
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self):
        """Start the trading bot"""
        if self.is_running:
            self.logger.warning("Bot is already running")
            return
        
        self.logger.info("Starting AxiomTradingBot...")
        self.is_running = True
        self.start_time = datetime.utcnow()
        
        try:
            # Start core components
            await self.event_manager.start()
            await self.notification_manager.start()
            
            # Connect to AxiomTrade API
            await self._connect_api()
            
            # Setup event subscriptions
            self._setup_event_subscriptions()
            
            # Start all strategies
            for strategy in self.strategies.values():
                await strategy.start()
            
            # Publish bot started event
            await self.event_manager.publish_bot_started("AxiomTradingBot")
            
            # Send startup notification
            await self.notification_manager.send_bot_notification(
                "🚀 AxiomTradingBot Started",
                f"Bot started with {len(self.strategies)} strategies active",
                "success"
            )
            
            self.logger.info("AxiomTradingBot started successfully")
            
            # Keep running until stopped
            await self._run_main_loop()
            
        except Exception as e:
            self.logger.error(f"Error starting bot: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the trading bot"""
        if not self.is_running:
            return
            
        self.logger.info("Stopping AxiomTradingBot...")
        self.is_running = False
        
        try:
            # Stop all strategies
            for strategy in self.strategies.values():
                await strategy.stop()
            
            # Stop core components
            await self.event_manager.stop()
            await self.notification_manager.stop()
            
            # Publish bot stopped event
            await self.event_manager.publish_bot_stopped("AxiomTradingBot")
            
            # Send shutdown notification
            runtime = (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0
            await self.notification_manager.send_bot_notification(
                "🛑 AxiomTradingBot Stopped",
                f"Bot stopped after {runtime:.0f} seconds\\nTotal trades: {self.total_trades}\\nTotal PnL: {self.total_pnl:.4f} SOL",
                "info"
            )
            
            self.logger.info("AxiomTradingBot stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping bot: {e}")
    
    async def pause(self):
        """Pause the trading bot"""
        self.logger.info("Pausing AxiomTradingBot...")
        self.is_paused = True
        
        for strategy in self.strategies.values():
            await strategy.pause()
            
        await self.notification_manager.send_bot_notification(
            "⏸️ AxiomTradingBot Paused",
            "All strategies have been paused",
            "warning"
        )
    
    async def resume(self):
        """Resume the trading bot"""
        self.logger.info("Resuming AxiomTradingBot...")
        self.is_paused = False
        
        for strategy in self.strategies.values():
            await strategy.resume()
            
        await self.notification_manager.send_bot_notification(
            "▶️ AxiomTradingBot Resumed",
            "All strategies have been resumed",
            "success"
        )
    
    async def _connect_api(self):
        """Connect to AxiomTrade API"""
        try:
            # Login to AxiomTrade
            login_result = self.api_client.login(
                email=self.config.axiom_trade.email,
                password=self.config.axiom_trade.password
            )
            
            if not login_result.get('success', False):
                raise Exception(f"Failed to login to AxiomTrade: {login_result.get('message', 'Unknown error')}")
            
            self.logger.info("Successfully connected to AxiomTrade API")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to AxiomTrade API: {e}")
            raise
    
    def _setup_event_subscriptions(self):
        """Setup event subscriptions for the bot"""
        # Subscribe to trading events
        self.event_manager.subscribe(EventType.TRADE_EXECUTED, self._on_trade_executed)
        self.event_manager.subscribe(EventType.POSITION_OPENED, self._on_position_opened)
        self.event_manager.subscribe(EventType.POSITION_CLOSED, self._on_position_closed)
        self.event_manager.subscribe(EventType.ERROR_OCCURRED, self._on_error_occurred)
    
    async def _run_main_loop(self):
        """Main bot loop"""
        while self.is_running:
            try:
                if not self.is_paused:
                    # Update position prices
                    await self._update_position_prices()
                    
                    # Check risk management
                    await self._check_risk_management()
                    
                    # Update performance metrics
                    await self._update_performance_metrics()
                
                # Sleep for main loop interval
                await asyncio.sleep(5.0)
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(10.0)
    
    def add_strategy(self, strategy: BaseStrategy):
        """
        Add a strategy to the bot
        
        Args:
            strategy: BaseStrategy instance to add
        """
        if strategy.name in self.strategies:
            self.logger.warning(f"Strategy {strategy.name} already exists, replacing...")
        
        self.strategies[strategy.name] = strategy
        self.logger.info(f"Added strategy: {strategy.name}")
    
    def remove_strategy(self, strategy_name: str):
        """
        Remove a strategy from the bot
        
        Args:
            strategy_name: Name of strategy to remove
        """
        if strategy_name in self.strategies:
            strategy = self.strategies[strategy_name]
            asyncio.create_task(strategy.stop())
            del self.strategies[strategy_name]
            self.logger.info(f"Removed strategy: {strategy_name}")
        else:
            self.logger.warning(f"Strategy {strategy_name} not found")
    
    async def execute_trade(self, signal: TradeSignal) -> bool:
        """
        Execute a trading signal
        
        Args:
            signal: TradeSignal to execute
            
        Returns:
            bool: True if execution was successful
        """
        try:
            # Check risk management first
            if not await self.risk_manager.can_execute_trade(signal):
                self.logger.warning(f"Trade blocked by risk management: {signal.token_address}")
                return False
            
            # Execute the trade via AxiomTrade API
            success, tx_hash, error = await self._execute_trade_api(signal)
            
            if success:
                self.logger.info(f"Successfully executed {signal.action} for {signal.token_address}")
                
                # Record trade in database
                trade_record = TradeRecord(
                    strategy_name=signal.metadata.get('strategy_name', 'Unknown'),
                    token_address=signal.token_address,
                    action=signal.action,
                    amount=signal.amount,
                    price=signal.price or 0.0,
                    timestamp=signal.timestamp,
                    tx_hash=tx_hash,
                    success=True,
                    metadata=signal.metadata
                )
                await self.database.record_trade(trade_record)
                
                # Publish trade executed event
                await self.event_manager.publish_trade_executed({
                    'signal': signal.__dict__,
                    'tx_hash': tx_hash,
                    'success': True
                }, "AxiomTradingBot")
                
                # Send notification
                await self.notification_manager.send_trade_notification(signal, True, tx_hash)
                
                self.total_trades += 1
                
            else:
                self.logger.error(f"Failed to execute {signal.action} for {signal.token_address}: {error}")
                
                # Record failed trade
                trade_record = TradeRecord(
                    strategy_name=signal.metadata.get('strategy_name', 'Unknown'),
                    token_address=signal.token_address,
                    action=signal.action,
                    amount=signal.amount,
                    price=signal.price or 0.0,
                    timestamp=signal.timestamp,
                    success=False,
                    error_message=error,
                    metadata=signal.metadata
                )
                await self.database.record_trade(trade_record)
                
                # Publish error event
                await self.event_manager.publish_error({
                    'message': f"Trade execution failed: {error}",
                    'signal': signal.__dict__
                }, "AxiomTradingBot")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            return False
    
    async def _execute_trade_api(self, signal: TradeSignal) -> tuple[bool, str, str]:
        """
        Execute trade via AxiomTrade API
        
        Returns:
            Tuple of (success, tx_hash, error_message)
        """
        try:
            if signal.action == "buy":
                # Execute buy order
                result = await self._execute_buy(signal)
            elif signal.action == "sell":
                # Execute sell order
                result = await self._execute_sell(signal)
            else:
                return False, "", f"Unknown action: {signal.action}"
            
            return result
            
        except Exception as e:
            return False, "", str(e)
    
    async def _execute_buy(self, signal: TradeSignal) -> tuple[bool, str, str]:
        """Execute a buy order"""
        try:
            # Use the AxiomTrade API to buy tokens
            # This is a placeholder - implement based on actual API methods
            response = self.api_client.buy_token(
                token_address=signal.token_address,
                amount_sol=signal.amount,
                slippage=self.config.trading.max_slippage
            )
            
            if response.get('success', False):
                return True, response.get('tx_hash', ''), ""
            else:
                return False, "", response.get('error', 'Unknown error')
                
        except Exception as e:
            return False, "", str(e)
    
    async def _execute_sell(self, signal: TradeSignal) -> tuple[bool, str, str]:
        """Execute a sell order"""
        try:
            # Use the AxiomTrade API to sell tokens
            # This is a placeholder - implement based on actual API methods
            response = self.api_client.sell_token(
                token_address=signal.token_address,
                amount_tokens=signal.amount,
                slippage=self.config.trading.max_slippage
            )
            
            if response.get('success', False):
                return True, response.get('tx_hash', ''), ""
            else:
                return False, "", response.get('error', 'Unknown error')
                
        except Exception as e:
            return False, "", str(e)
    
    async def _update_position_prices(self):
        """Update current prices for all open positions"""
        try:
            open_positions = await self.database.get_open_positions()
            
            for position in open_positions:
                # Get current price for the token
                current_price = await self._get_token_price(position.token_address)
                
                if current_price:
                    # Update position in database
                    unrealized_pnl = (current_price - position.entry_price) * position.amount
                    
                    await self.database.update_position(
                        position.id,
                        current_price=current_price,
                        unrealized_pnl=unrealized_pnl
                    )
                    
                    # Update strategy positions
                    for strategy in self.strategies.values():
                        strategy.update_position_price(position.token_address, current_price)
                        
        except Exception as e:
            self.logger.error(f"Error updating position prices: {e}")
    
    async def _get_token_price(self, token_address: str) -> Optional[float]:
        """Get current price for a token"""
        try:
            # Use AxiomTrade API to get token price
            # This is a placeholder - implement based on actual API methods
            price_data = self.api_client.get_token_price(token_address)
            return price_data.get('price', 0.0)
            
        except Exception as e:
            self.logger.error(f"Error getting price for {token_address}: {e}")
            return None
    
    async def _check_risk_management(self):
        """Check risk management rules"""
        try:
            # Get current performance stats
            stats = await self.database.get_performance_stats(days=1)
            
            # Check daily loss limit
            if stats.get('total_pnl', 0) < -self.config.risk_management.max_daily_loss:
                self.logger.warning("Daily loss limit exceeded, pausing bot")
                await self.pause()
                
                await self.notification_manager.send_risk_notification(
                    "Daily Loss Limit Exceeded",
                    f"Daily PnL: {stats.get('total_pnl', 0):.4f} SOL",
                    "error"
                )
            
            # Check emergency stop loss
            total_pnl_percent = abs(stats.get('total_pnl', 0)) / self.config.trading.max_position_size * 100
            if total_pnl_percent > self.config.risk_management.emergency_stop_loss:
                self.logger.error("Emergency stop loss triggered, stopping bot")
                await self.stop()
                
                await self.notification_manager.send_risk_notification(
                    "Emergency Stop Loss Triggered",
                    f"Total loss: {total_pnl_percent:.1f}%",
                    "error"
                )
                
        except Exception as e:
            self.logger.error(f"Error checking risk management: {e}")
    
    async def _update_performance_metrics(self):
        """Update performance metrics"""
        try:
            stats = await self.database.get_performance_stats(days=1)
            self.daily_pnl = stats.get('total_pnl', 0.0)
            
            # Update total PnL
            total_stats = await self.database.get_performance_stats(days=365)
            self.total_pnl = total_stats.get('total_pnl', 0.0)
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    # Event handlers
    async def _on_trade_executed(self, event):
        """Handle trade executed events"""
        self.logger.debug(f"Trade executed: {event.data}")
    
    async def _on_position_opened(self, event):
        """Handle position opened events"""
        self.logger.debug(f"Position opened: {event.data}")
    
    async def _on_position_closed(self, event):
        """Handle position closed events"""
        self.logger.debug(f"Position closed: {event.data}")
    
    async def _on_error_occurred(self, event):
        """Handle error events"""
        self.logger.error(f"Error occurred: {event.data}")
        
        # Send error notification
        await self.notification_manager.send_error_notification(
            event.data.get('message', 'Unknown error'),
            event.data
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status"""
        runtime = (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0
        
        strategy_stats = {}
        for name, strategy in self.strategies.items():
            strategy_stats[name] = strategy.get_performance_stats()
        
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "runtime_seconds": runtime,
            "total_trades": self.total_trades,
            "total_pnl": self.total_pnl,
            "daily_pnl": self.daily_pnl,
            "active_strategies": len(self.strategies),
            "strategies": strategy_stats
        }
    
    async def get_performance_report(self, days: int = 7) -> Dict[str, Any]:
        """Get performance report"""
        return await self.database.get_performance_stats(days=days)
