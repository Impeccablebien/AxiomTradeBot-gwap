"""
Wallet Tracker Strategy for AxiomTradingBot
Monitors specified wallets and copies their trading activities
"""

import asyncio
import logging
from typing import Dict, Any, List, Set, Optional
from datetime import datetime, timedelta

from ..core.base_strategy import BaseStrategy, TradeSignal, Position
from ..core.event_manager import EventType

class WalletTracker(BaseStrategy):
    """
    Strategy for tracking and copying trades from profitable wallets
    """
    
    def __init__(self, bot, target_wallets: List[str] = None, config: Dict[str, Any] = None):
        """
        Initialize WalletTracker strategy
        
        Args:
            bot: Reference to main trading bot
            target_wallets: List of wallet addresses to track
            config: Strategy configuration
        """
        super().__init__(bot, "WalletTracker", config)
        
        # Strategy configuration with defaults
        self.target_wallets: Set[str] = set(target_wallets or [])
        self.copy_percentage = config.get('copy_percentage', 50.0)  # % of their trade size
        self.min_trade_size = config.get('min_trade_size', 0.01)  # SOL
        self.max_copy_amount = config.get('max_copy_amount', 1.0)  # SOL
        self.take_profit = config.get('take_profit', 100.0)  # %
        self.stop_loss = config.get('stop_loss', 20.0)  # %
        self.delay_seconds = config.get('delay_seconds', 1)  # Delay before copying
        self.blacklisted_tokens = set(config.get('blacklisted_tokens', []))
        self.whitelisted_tokens = set(config.get('whitelisted_tokens', []))
        
        # Internal state
        self.wallet_stats: Dict[str, Dict[str, Any]] = {}
        self.processed_transactions: Set[str] = set()
        self.pending_copies: Dict[str, datetime] = {}  # tx_hash -> timestamp
        
        # Initialize wallet stats
        for wallet in self.target_wallets:
            self.wallet_stats[wallet] = {
                'total_trades': 0,
                'profitable_trades': 0,
                'total_profit': 0.0,
                'win_rate': 0.0,
                'last_activity': None
            }
        
        self.logger.info(f"WalletTracker initialized tracking {len(self.target_wallets)} wallets")
    
    async def initialize(self):
        """Initialize the wallet tracker strategy"""
        self.logger.info("Initializing WalletTracker strategy...")
        
        # Subscribe to wallet transaction events
        self.bot.event_manager.subscribe(EventType.WALLET_TRANSACTION, self.on_wallet_transaction)
        self.bot.event_manager.subscribe(EventType.PRICE_UPDATE, self.on_price_update)
        
        # Setup WebSocket monitoring for target wallets
        await self._setup_wallet_monitoring()
        
        # Load historical wallet performance
        await self._load_wallet_performance()
        
        self.logger.info("WalletTracker strategy initialized")
    
    async def execute(self):
        """Main execution logic (called repeatedly)"""
        try:
            # Clean up old pending copies
            current_time = datetime.utcnow()
            expired_copies = [
                tx_hash for tx_hash, timestamp in self.pending_copies.items()
                if (current_time - timestamp).total_seconds() > 300  # 5 minutes
            ]
            
            for tx_hash in expired_copies:
                del self.pending_copies[tx_hash]
                self.logger.debug(f"Removed expired pending copy for {tx_hash}")
            
            # Update wallet performance stats
            await self._update_wallet_stats()
            
        except Exception as e:
            self.logger.error(f"Error in WalletTracker execution: {e}")
    
    async def cleanup(self):
        """Cleanup strategy resources"""
        self.logger.info("Cleaning up WalletTracker strategy...")
        
        # Unsubscribe from events
        self.bot.event_manager.unsubscribe(EventType.WALLET_TRANSACTION, self.on_wallet_transaction)
        self.bot.event_manager.unsubscribe(EventType.PRICE_UPDATE, self.on_price_update)
        
        self.logger.info("WalletTracker strategy cleaned up")
    
    def add_wallet(self, wallet_address: str):
        """Add a wallet to track"""
        if wallet_address not in self.target_wallets:
            self.target_wallets.add(wallet_address)
            self.wallet_stats[wallet_address] = {
                'total_trades': 0,
                'profitable_trades': 0,
                'total_profit': 0.0,
                'win_rate': 0.0,
                'last_activity': None
            }
            self.logger.info(f"Added wallet to tracking: {wallet_address}")
    
    def remove_wallet(self, wallet_address: str):
        """Remove a wallet from tracking"""
        if wallet_address in self.target_wallets:
            self.target_wallets.remove(wallet_address)
            if wallet_address in self.wallet_stats:
                del self.wallet_stats[wallet_address]
            self.logger.info(f"Removed wallet from tracking: {wallet_address}")
    
    async def on_wallet_transaction(self, event):
        """Handle wallet transaction events"""
        try:
            transaction_data = event.data
            wallet_address = transaction_data.get('wallet_address', '')
            
            # Check if this is one of our target wallets
            if wallet_address not in self.target_wallets:
                return
            
            # Skip if already processed
            tx_hash = transaction_data.get('tx_hash', '')
            if tx_hash in self.processed_transactions:
                return
            
            self.processed_transactions.add(tx_hash)
            
            self.logger.info(f"Transaction detected from tracked wallet {wallet_address[:8]}...")
            
            # Analyze transaction for copy trading opportunity
            should_copy = await self._analyze_transaction_for_copying(transaction_data)
            
            if should_copy:
                await self._execute_copy_trade(transaction_data)
            else:
                self.logger.debug(f"Transaction {tx_hash[:8]}... did not meet copying criteria")
                
        except Exception as e:
            self.logger.error(f"Error handling wallet transaction event: {e}")
    
    async def _analyze_transaction_for_copying(self, transaction_data: Dict[str, Any]) -> bool:
        """
        Analyze a wallet transaction to determine if it should be copied
        
        Args:
            transaction_data: Transaction information
            
        Returns:
            bool: True if transaction should be copied
        """
        try:
            tx_type = transaction_data.get('type', '').lower()
            token_address = transaction_data.get('token_address', '')
            amount_sol = transaction_data.get('amount_sol', 0.0)
            wallet_address = transaction_data.get('wallet_address', '')
            
            # Only copy buy transactions for now
            if tx_type != 'buy':
                self.logger.debug(f"Skipping non-buy transaction: {tx_type}")
                return False
            
            # Check minimum trade size
            if amount_sol < self.min_trade_size:
                self.logger.debug(f"Trade size too small: {amount_sol} < {self.min_trade_size}")
                return False
            
            # Check blacklist
            if token_address in self.blacklisted_tokens:
                self.logger.debug(f"Token {token_address} is blacklisted")
                return False
            
            # If whitelist exists, only copy whitelisted tokens
            if self.whitelisted_tokens and token_address not in self.whitelisted_tokens:
                self.logger.debug(f"Token {token_address} not in whitelist")
                return False
            
            # Check wallet performance (only copy from profitable wallets)
            wallet_stats = self.wallet_stats.get(wallet_address, {})
            win_rate = wallet_stats.get('win_rate', 0.0)
            total_trades = wallet_stats.get('total_trades', 0)
            
            # Require at least 5 trades and 60% win rate
            if total_trades >= 5 and win_rate < 60.0:
                self.logger.debug(f"Wallet {wallet_address[:8]}... has low win rate: {win_rate:.1f}%")
                return False
            
            # Check if we already have a position in this token
            if token_address in self.positions:
                self.logger.debug(f"Already have position in {token_address}")
                return False
            
            # Check max positions
            if len(self.positions) >= 10:  # Configurable max
                self.logger.debug("Max positions reached")
                return False
            
            self.logger.info(f"Transaction from {wallet_address[:8]}... passed copying criteria")
            return True
            
        except Exception as e:
            self.logger.error(f"Error analyzing transaction: {e}")
            return False
    
    async def _execute_copy_trade(self, transaction_data: Dict[str, Any]):
        """
        Execute a copy trade based on wallet transaction
        
        Args:
            transaction_data: Original transaction data
        """
        try:
            token_address = transaction_data.get('token_address', '')
            original_amount = transaction_data.get('amount_sol', 0.0)
            wallet_address = transaction_data.get('wallet_address', '')
            tx_hash = transaction_data.get('tx_hash', '')
            
            # Calculate copy amount
            copy_amount = original_amount * (self.copy_percentage / 100.0)
            copy_amount = min(copy_amount, self.max_copy_amount)
            
            # Add to pending copies
            self.pending_copies[tx_hash] = datetime.utcnow()
            
            # Optional delay before copying
            if self.delay_seconds > 0:
                await asyncio.sleep(self.delay_seconds)
            
            # Get current price
            current_price = await self._get_token_price(token_address)
            if not current_price:
                self.logger.error(f"Could not get price for {token_address}")
                if tx_hash in self.pending_copies:
                    del self.pending_copies[tx_hash]
                return
            
            # Generate buy signal
            signal = self.generate_signal(
                action="buy",
                token_address=token_address,
                amount=copy_amount,
                confidence=0.9,  # High confidence for copy trades
                reason=f"Copy trade from wallet {wallet_address[:8]}... (original: {original_amount:.4f} SOL)",
                strategy_name=self.name,
                original_wallet=wallet_address,
                original_amount=original_amount,
                original_tx=tx_hash,
                copy_percentage=self.copy_percentage
            )
            
            signal.price = current_price
            
            # Execute the buy
            success = await self.execute_signal(signal)
            
            if success:
                # Create position
                position = Position(
                    token_address=token_address,
                    amount=copy_amount,
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
                    amount=copy_amount,
                    entry_time=datetime.utcnow(),
                    take_profit=self.take_profit,
                    stop_loss=self.stop_loss
                )
                
                await self.bot.database.record_position(position_record)
                
                self.logger.info(f"Successfully copied trade: {copy_amount:.4f} SOL in {token_address}")
                
                # Update wallet stats
                self.wallet_stats[wallet_address]['last_activity'] = datetime.utcnow()
                
                # Publish position opened event
                await self.bot.event_manager.publish_position_opened({
                    'strategy': self.name,
                    'token_address': token_address,
                    'amount': copy_amount,
                    'entry_price': current_price,
                    'copied_from': wallet_address
                }, self.name)
                
            else:
                self.logger.error(f"Failed to copy trade for {token_address}")
            
            # Remove from pending
            if tx_hash in self.pending_copies:
                del self.pending_copies[tx_hash]
                
        except Exception as e:
            self.logger.error(f"Error executing copy trade: {e}")
            
            # Clean up
            tx_hash = transaction_data.get('tx_hash', '')
            if tx_hash in self.pending_copies:
                del self.pending_copies[tx_hash]
    
    async def _setup_wallet_monitoring(self):
        """Setup WebSocket monitoring for target wallets"""
        try:
            for wallet_address in self.target_wallets:
                # Subscribe to wallet transaction updates
                await self.bot.api_client.subscribe_wallet_transactions(
                    wallet_address, 
                    self._handle_websocket_wallet_transaction
                )
            
            self.logger.info(f"WebSocket monitoring setup for {len(self.target_wallets)} wallets")
        except Exception as e:
            self.logger.error(f"Error setting up wallet monitoring: {e}")
    
    async def _handle_websocket_wallet_transaction(self, transaction_data: Dict[str, Any]):
        """Handle wallet transaction from WebSocket"""
        try:
            # Publish wallet transaction event
            await self.bot.event_manager.publish_wallet_transaction(
                transaction_data.get('wallet_address', ''),
                transaction_data,
                "WalletTracker"
            )
        except Exception as e:
            self.logger.error(f"Error handling WebSocket wallet transaction: {e}")
    
    async def _load_wallet_performance(self):
        """Load historical performance data for tracked wallets"""
        try:
            # This would typically load from a database or API
            # For now, we'll initialize with default values
            self.logger.info("Loading wallet performance data...")
            
            # TODO: Implement actual performance loading from database
            # This could analyze past transactions to calculate win rates
            
        except Exception as e:
            self.logger.error(f"Error loading wallet performance: {e}")
    
    async def _update_wallet_stats(self):
        """Update wallet performance statistics"""
        try:
            # This would be called periodically to update stats
            # For now, it's a placeholder
            pass
        except Exception as e:
            self.logger.error(f"Error updating wallet stats: {e}")
    
    async def _get_token_price(self, token_address: str) -> Optional[float]:
        """Get current price for a token"""
        try:
            # Use the bot's price fetching method
            return await self.bot._get_token_price(token_address)
        except Exception as e:
            self.logger.error(f"Error getting price for {token_address}: {e}")
            return None
    
    def get_tracker_stats(self) -> Dict[str, Any]:
        """Get wallet tracker specific statistics"""
        stats = self.get_performance_stats()
        
        stats.update({
            "tracked_wallets": len(self.target_wallets),
            "processed_transactions": len(self.processed_transactions),
            "pending_copies": len(self.pending_copies),
            "copy_percentage": self.copy_percentage,
            "min_trade_size": self.min_trade_size,
            "max_copy_amount": self.max_copy_amount,
            "wallet_stats": self.wallet_stats
        })
        
        return stats
    
    def get_wallet_performance(self, wallet_address: str) -> Dict[str, Any]:
        """Get performance stats for a specific wallet"""
        return self.wallet_stats.get(wallet_address, {})
    
    def get_top_performing_wallets(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top performing wallets by win rate"""
        wallet_list = []
        
        for wallet, stats in self.wallet_stats.items():
            if stats.get('total_trades', 0) >= 5:  # Minimum trades for ranking
                wallet_list.append({
                    'address': wallet,
                    'win_rate': stats.get('win_rate', 0.0),
                    'total_trades': stats.get('total_trades', 0),
                    'total_profit': stats.get('total_profit', 0.0)
                })
        
        # Sort by win rate, then by total profit
        wallet_list.sort(key=lambda x: (x['win_rate'], x['total_profit']), reverse=True)
        
        return wallet_list[:limit]
