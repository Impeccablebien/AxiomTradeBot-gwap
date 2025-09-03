"""
Token Sniper Strategy for AxiomTradingBot
Automatically detects and purchases new tokens based on predefined criteria
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..core.base_strategy import BaseStrategy, TradeSignal, Position
from ..core.event_manager import EventType

class TokenSniper(BaseStrategy):
    """
    Strategy for sniping new tokens based on liquidity, taxes, and other criteria
    """
    
    def __init__(self, bot, config: Dict[str, Any] = None):
        """
        Initialize TokenSniper strategy
        
        Args:
            bot: Reference to main trading bot
            config: Strategy configuration
        """
        super().__init__(bot, "TokenSniper", config)
        
        # Strategy configuration with defaults
        self.buy_amount = config.get('buy_amount', 0.05)  # SOL
        self.min_liquidity = config.get('min_liquidity', 10.0)  # SOL
        self.max_buy_tax = config.get('max_buy_tax', 5.0)  # %
        self.max_sell_tax = config.get('max_sell_tax', 5.0)  # %
        self.take_profit = config.get('take_profit', 100.0)  # %
        self.stop_loss = config.get('stop_loss', 15.0)  # %
        self.blacklisted_tokens = set(config.get('blacklisted_tokens', []))
        self.whitelisted_tokens = set(config.get('whitelisted_tokens', []))
        self.auto_sell_delay = config.get('auto_sell_delay', 60)  # seconds
        self.max_positions = config.get('max_positions', 5)
        
        # Internal state
        self.processed_tokens = set()
        self.pending_buys = {}  # token_address -> timestamp
        self.auto_sell_tasks = {}  # token_address -> asyncio.Task
        
        self.logger.info(f"TokenSniper initialized with buy_amount={self.buy_amount} SOL")
    
    async def initialize(self):
        """Initialize the token sniper strategy"""
        self.logger.info("Initializing TokenSniper strategy...")
        
        # Subscribe to new token events
        self.bot.event_manager.subscribe(EventType.NEW_TOKEN, self.on_new_token)
        self.bot.event_manager.subscribe(EventType.PRICE_UPDATE, self.on_price_update)
        
        # Connect to WebSocket for real-time token detection
        await self._setup_websocket_monitoring()
        
        self.logger.info("TokenSniper strategy initialized")
    
    async def execute(self):
        """Main execution logic (called repeatedly)"""
        try:
            # Clean up old pending buys (remove after 5 minutes)
            current_time = datetime.utcnow()
            expired_tokens = [
                token for token, timestamp in self.pending_buys.items()
                if (current_time - timestamp).total_seconds() > 300
            ]
            
            for token in expired_tokens:
                del self.pending_buys[token]
                self.logger.debug(f"Removed expired pending buy for {token}")
            
            # Check if we need to close any positions due to auto-sell
            await self._check_auto_sell_positions()
            
        except Exception as e:
            self.logger.error(f"Error in TokenSniper execution: {e}")
    
    async def cleanup(self):
        """Cleanup strategy resources"""
        self.logger.info("Cleaning up TokenSniper strategy...")
        
        # Cancel auto-sell tasks
        for task in self.auto_sell_tasks.values():
            if not task.done():
                task.cancel()
        
        # Unsubscribe from events
        self.bot.event_manager.unsubscribe(EventType.NEW_TOKEN, self.on_new_token)
        self.bot.event_manager.unsubscribe(EventType.PRICE_UPDATE, self.on_price_update)
        
        self.logger.info("TokenSniper strategy cleaned up")
    
    async def on_new_token(self, event):
        """Handle new token detection events"""
        try:
            token_data = event.data
            token_address = token_data.get('address', '')
            
            if not token_address:
                return
            
            # Skip if already processed
            if token_address in self.processed_tokens:
                return
            
            self.processed_tokens.add(token_address)
            
            self.logger.info(f"New token detected: {token_address}")
            
            # Analyze token for sniping opportunity
            should_snipe = await self._analyze_token_for_sniping(token_data)
            
            if should_snipe:
                await self._execute_snipe(token_data)
            else:
                self.logger.debug(f"Token {token_address} did not meet sniping criteria")
                
        except Exception as e:
            self.logger.error(f"Error handling new token event: {e}")
    
    async def _analyze_token_for_sniping(self, token_data: Dict[str, Any]) -> bool:
        """
        Analyze a token to determine if it should be sniped
        
        Args:
            token_data: Token information
            
        Returns:
            bool: True if token should be sniped
        """
        try:
            token_address = token_data.get('address', '')
            
            # Check blacklist
            if token_address in self.blacklisted_tokens:
                self.logger.debug(f"Token {token_address} is blacklisted")
                return False
            
            # If whitelist exists, only trade whitelisted tokens
            if self.whitelisted_tokens and token_address not in self.whitelisted_tokens:
                self.logger.debug(f"Token {token_address} not in whitelist")
                return False
            
            # Check if we're at max positions
            if len(self.positions) >= self.max_positions:
                self.logger.debug(f"Max positions ({self.max_positions}) reached")
                return False
            
            # Check liquidity requirement
            liquidity = token_data.get('liquidity', 0)
            if liquidity < self.min_liquidity:
                self.logger.debug(f"Insufficient liquidity: {liquidity} < {self.min_liquidity}")
                return False
            
            # Check buy tax
            buy_tax = token_data.get('buy_tax', 0)
            if buy_tax > self.max_buy_tax:
                self.logger.debug(f"Buy tax too high: {buy_tax}% > {self.max_buy_tax}%")
                return False
            
            # Check sell tax
            sell_tax = token_data.get('sell_tax', 0)
            if sell_tax > self.max_sell_tax:
                self.logger.debug(f"Sell tax too high: {sell_tax}% > {self.max_sell_tax}%")
                return False
            
            # Additional checks can be added here:
            # - Contract verification
            # - Honeypot detection
            # - Social signals
            # - Volume requirements
            
            self.logger.info(f"Token {token_address} passed all sniping criteria")
            return True
            
        except Exception as e:
            self.logger.error(f"Error analyzing token {token_data.get('address', '')}: {e}")
            return False
    
    async def _execute_snipe(self, token_data: Dict[str, Any]):
        """
        Execute a token snipe
        
        Args:
            token_data: Token information
        """
        try:
            token_address = token_data.get('address', '')
            
            # Check if already pending
            if token_address in self.pending_buys:
                self.logger.debug(f"Buy already pending for {token_address}")
                return
            
            self.pending_buys[token_address] = datetime.utcnow()
            
            # Get current price for the token
            current_price = await self._get_token_price(token_address)
            if not current_price:
                self.logger.error(f"Could not get price for {token_address}")
                del self.pending_buys[token_address]
                return
            
            # Generate buy signal
            signal = self.generate_signal(
                action="buy",
                token_address=token_address,
                amount=self.buy_amount,
                confidence=0.8,  # Medium confidence for new tokens
                reason=f"Token snipe - Liquidity: {token_data.get('liquidity', 0):.2f} SOL",
                strategy_name=self.name,
                token_data=token_data,
                snipe_timestamp=datetime.utcnow().isoformat()
            )
            
            signal.price = current_price
            
            # Execute the buy
            success = await self.execute_signal(signal)
            
            if success:
                # Create position
                position = Position(
                    token_address=token_address,
                    amount=self.buy_amount,
                    entry_price=current_price,
                    entry_time=datetime.utcnow(),
                    take_profit=self.take_profit,
                    stop_loss=self.stop_loss
                )
                
                self.add_position(position)
                
                # Record position in database
                from ..core.database import PositionRecord
                position_record = PositionRecord(
                    strategy_name=self.name,
                    token_address=token_address,
                    entry_price=current_price,
                    current_price=current_price,
                    amount=self.buy_amount,
                    entry_time=datetime.utcnow(),
                    take_profit=self.take_profit,
                    stop_loss=self.stop_loss
                )
                
                await self.bot.database.record_position(position_record)
                
                # Setup auto-sell if configured
                if self.auto_sell_delay > 0:
                    self._schedule_auto_sell(token_address, self.auto_sell_delay)
                
                self.logger.info(f"Successfully sniped token {token_address} at {current_price}")
                
                # Publish position opened event
                await self.bot.event_manager.publish_position_opened({
                    'strategy': self.name,
                    'token_address': token_address,
                    'amount': self.buy_amount,
                    'entry_price': current_price
                }, self.name)
                
            else:
                self.logger.error(f"Failed to snipe token {token_address}")
            
            # Remove from pending
            if token_address in self.pending_buys:
                del self.pending_buys[token_address]
                
        except Exception as e:
            self.logger.error(f"Error executing snipe for {token_data.get('address', '')}: {e}")
            
            # Clean up
            token_address = token_data.get('address', '')
            if token_address in self.pending_buys:
                del self.pending_buys[token_address]
    
    def _schedule_auto_sell(self, token_address: str, delay_seconds: int):
        """Schedule an auto-sell for a token"""
        async def auto_sell_task():
            try:
                await asyncio.sleep(delay_seconds)
                
                if token_address in self.positions:
                    position = self.positions[token_address]
                    
                    # Get current price
                    current_price = await self._get_token_price(token_address)
                    if not current_price:
                        self.logger.error(f"Could not get price for auto-sell of {token_address}")
                        return
                    
                    # Generate sell signal
                    signal = self.generate_signal(
                        action="sell",
                        token_address=token_address,
                        amount=position.amount,
                        confidence=1.0,
                        reason=f"Auto-sell after {delay_seconds}s delay",
                        strategy_name=self.name,
                        auto_sell=True
                    )
                    
                    signal.price = current_price
                    
                    # Execute the sell
                    success = await self.execute_signal(signal)
                    
                    if success:
                        self.close_position(token_address, current_price, "auto_sell")
                        self.logger.info(f"Auto-sold {token_address} after {delay_seconds}s")
                    
            except asyncio.CancelledError:
                self.logger.debug(f"Auto-sell task cancelled for {token_address}")
            except Exception as e:
                self.logger.error(f"Error in auto-sell task for {token_address}: {e}")
            finally:
                # Clean up task reference
                if token_address in self.auto_sell_tasks:
                    del self.auto_sell_tasks[token_address]
        
        # Cancel existing auto-sell task if any
        if token_address in self.auto_sell_tasks:
            self.auto_sell_tasks[token_address].cancel()
        
        # Schedule new auto-sell task
        task = asyncio.create_task(auto_sell_task())
        self.auto_sell_tasks[token_address] = task
        
        self.logger.info(f"Scheduled auto-sell for {token_address} in {delay_seconds}s")
    
    async def _check_auto_sell_positions(self):
        """Check positions for auto-sell conditions"""
        try:
            current_time = datetime.utcnow()
            
            for token_address, position in list(self.positions.items()):
                # Check if position has been open for too long
                time_open = (current_time - position.entry_time).total_seconds()
                
                # Auto-sell if position is open for more than 5 minutes and no auto-sell scheduled
                if (time_open > 300 and 
                    token_address not in self.auto_sell_tasks and 
                    self.auto_sell_delay == 0):
                    
                    self.logger.info(f"Auto-selling stale position {token_address} after {time_open:.0f}s")
                    self._schedule_auto_sell(token_address, 0)  # Immediate sale
                    
        except Exception as e:
            self.logger.error(f"Error checking auto-sell positions: {e}")
    
    async def _get_token_price(self, token_address: str) -> Optional[float]:
        """Get current price for a token"""
        try:
            # Use the bot's price fetching method
            return await self.bot._get_token_price(token_address)
        except Exception as e:
            self.logger.error(f"Error getting price for {token_address}: {e}")
            return None
    
    async def _setup_websocket_monitoring(self):
        """Setup WebSocket monitoring for new tokens"""
        try:
            # Subscribe to new token updates via WebSocket
            await self.bot.api_client.subscribe_new_tokens(self._handle_websocket_new_token)
            self.logger.info("WebSocket monitoring setup for new tokens")
        except Exception as e:
            self.logger.error(f"Error setting up WebSocket monitoring: {e}")
    
    async def _handle_websocket_new_token(self, token_data: Dict[str, Any]):
        """Handle new token from WebSocket"""
        try:
            # Publish new token event
            await self.bot.event_manager.publish_new_token(token_data, "TokenSniper")
        except Exception as e:
            self.logger.error(f"Error handling WebSocket new token: {e}")
    
    def get_sniper_stats(self) -> Dict[str, Any]:
        """Get token sniper specific statistics"""
        stats = self.get_performance_stats()
        
        stats.update({
            "processed_tokens": len(self.processed_tokens),
            "pending_buys": len(self.pending_buys),
            "auto_sell_tasks": len(self.auto_sell_tasks),
            "buy_amount": self.buy_amount,
            "min_liquidity": self.min_liquidity,
            "max_buy_tax": self.max_buy_tax,
            "max_sell_tax": self.max_sell_tax
        })
        
        return stats
