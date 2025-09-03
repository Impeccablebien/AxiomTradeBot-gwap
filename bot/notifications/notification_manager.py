"""
Notification Manager for AxiomTradingBot
Coordinates all notification systems
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from .discord_notifier import DiscordNotifier
from ..core.config_manager import NotificationConfig
from ..core.base_strategy import TradeSignal

class NotificationManager:
    """
    Manages all notification systems for the bot
    """
    
    def __init__(self, config: NotificationConfig):
        """
        Initialize NotificationManager
        
        Args:
            config: Notification configuration
        """
        self.config = config
        self.logger = logging.getLogger("NotificationManager")
        
        # Initialize notifiers
        self.discord_notifier = None
        if config.discord_enabled and config.discord_webhook_url:
            self.discord_notifier = DiscordNotifier(config.discord_webhook_url)
        
        # Notification queue for rate limiting
        self.notification_queue = asyncio.Queue()
        self.is_running = False
        
        self.logger.info("NotificationManager initialized")
    
    async def start(self):
        """Start the notification manager"""
        if self.is_running:
            return
            
        self.is_running = True
        self.logger.info("Starting NotificationManager...")
        
        # Start notification processing task
        asyncio.create_task(self._process_notifications())
        
    async def stop(self):
        """Stop the notification manager"""
        self.is_running = False
        self.logger.info("NotificationManager stopped")
    
    async def _process_notifications(self):
        """Process notifications from the queue"""
        while self.is_running:
            try:
                # Wait for notification with timeout
                notification = await asyncio.wait_for(
                    self.notification_queue.get(), 
                    timeout=1.0
                )
                
                await self._send_notification(notification)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing notification: {e}")
                await asyncio.sleep(1)
    
    async def _send_notification(self, notification: Dict[str, Any]):
        """Send a notification via all enabled channels"""
        try:
            notification_type = notification.get('type', 'unknown')
            
            # Send via Discord if enabled
            if self.discord_notifier:
                try:
                    await self._send_discord_notification(notification)
                except Exception as e:
                    self.logger.error(f"Error sending Discord notification: {e}")
            
            # Add other notification channels here (email, telegram, etc.)
            
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
    
    async def _send_discord_notification(self, notification: Dict[str, Any]):
        """Send notification via Discord"""
        notification_type = notification.get('type', 'unknown')
        data = notification.get('data', {})
        
        if notification_type == 'trade':
            await self.discord_notifier.send_trade_notification(
                action=data.get('action', ''),
                token_address=data.get('token_address', ''),
                amount=data.get('amount', 0),
                price=data.get('price', 0),
                success=data.get('success', False),
                tx_hash=data.get('tx_hash', ''),
                reason=data.get('reason', '')
            )
        elif notification_type == 'position':
            await self.discord_notifier.send_position_notification(
                action=data.get('action', ''),
                token_address=data.get('token_address', ''),
                amount=data.get('amount', 0),
                entry_price=data.get('entry_price', 0),
                current_price=data.get('current_price'),
                pnl=data.get('pnl')
            )
        elif notification_type == 'bot':
            await self.discord_notifier.send_bot_notification(
                title=data.get('title', ''),
                message=data.get('message', ''),
                notification_type=data.get('level', 'info')
            )
        elif notification_type == 'performance':
            await self.discord_notifier.send_performance_report(data)
        elif notification_type == 'error':
            await self.discord_notifier.send_error_notification(
                error_message=data.get('message', ''),
                details=data.get('details', {})
            )
        elif notification_type == 'risk':
            await self.discord_notifier.send_bot_notification(
                title=data.get('title', 'Risk Alert'),
                message=data.get('message', ''),
                notification_type='warning'
            )
    
    async def send_trade_notification(self, signal: TradeSignal, success: bool, 
                                    tx_hash: str = "") -> bool:
        """
        Send a trade notification
        
        Args:
            signal: TradeSignal that was executed
            success: Whether the trade was successful
            tx_hash: Transaction hash
            
        Returns:
            bool: True if notification was queued
        """
        if not self.config.enable_trade_alerts:
            return False
            
        try:
            notification = {
                'type': 'trade',
                'data': {
                    'action': signal.action,
                    'token_address': signal.token_address,
                    'amount': signal.amount,
                    'price': signal.price or 0,
                    'success': success,
                    'tx_hash': tx_hash,
                    'reason': signal.reason
                }
            }
            
            await self.notification_queue.put(notification)
            return True
            
        except Exception as e:
            self.logger.error(f"Error queuing trade notification: {e}")
            return False
    
    async def send_position_notification(self, action: str, token_address: str,
                                       amount: float, entry_price: float,
                                       current_price: float = None, pnl: float = None) -> bool:
        """
        Send a position notification
        
        Args:
            action: 'opened' or 'closed'
            token_address: Token contract address
            amount: Position amount
            entry_price: Entry price
            current_price: Current price (for closed positions)
            pnl: Profit/Loss (for closed positions)
            
        Returns:
            bool: True if notification was queued
        """
        try:
            notification = {
                'type': 'position',
                'data': {
                    'action': action,
                    'token_address': token_address,
                    'amount': amount,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'pnl': pnl
                }
            }
            
            await self.notification_queue.put(notification)
            return True
            
        except Exception as e:
            self.logger.error(f"Error queuing position notification: {e}")
            return False
    
    async def send_bot_notification(self, title: str, message: str, 
                                   level: str = "info") -> bool:
        """
        Send a bot status notification
        
        Args:
            title: Notification title
            message: Notification message
            level: 'info', 'warning', 'error', 'success'
            
        Returns:
            bool: True if notification was queued
        """
        try:
            notification = {
                'type': 'bot',
                'data': {
                    'title': title,
                    'message': message,
                    'level': level
                }
            }
            
            await self.notification_queue.put(notification)
            return True
            
        except Exception as e:
            self.logger.error(f"Error queuing bot notification: {e}")
            return False
    
    async def send_performance_notification(self, stats: Dict[str, Any]) -> bool:
        """
        Send a performance report notification
        
        Args:
            stats: Performance statistics
            
        Returns:
            bool: True if notification was queued
        """
        try:
            notification = {
                'type': 'performance',
                'data': stats
            }
            
            await self.notification_queue.put(notification)
            return True
            
        except Exception as e:
            self.logger.error(f"Error queuing performance notification: {e}")
            return False
    
    async def send_error_notification(self, error_message: str, 
                                    details: Dict[str, Any] = None) -> bool:
        """
        Send an error notification
        
        Args:
            error_message: Error message
            details: Additional error details
            
        Returns:
            bool: True if notification was queued
        """
        if not self.config.enable_error_alerts:
            return False
            
        try:
            notification = {
                'type': 'error',
                'data': {
                    'message': error_message,
                    'details': details or {}
                }
            }
            
            await self.notification_queue.put(notification)
            return True
            
        except Exception as e:
            self.logger.error(f"Error queuing error notification: {e}")
            return False
    
    async def send_risk_notification(self, title: str, message: str, 
                                   level: str = "warning") -> bool:
        """
        Send a risk management notification
        
        Args:
            title: Alert title
            message: Alert message
            level: 'warning' or 'error'
            
        Returns:
            bool: True if notification was queued
        """
        try:
            notification = {
                'type': 'risk',
                'data': {
                    'title': title,
                    'message': message,
                    'level': level
                }
            }
            
            await self.notification_queue.put(notification)
            return True
            
        except Exception as e:
            self.logger.error(f"Error queuing risk notification: {e}")
            return False
    
    async def send_daily_report(self, stats: Dict[str, Any]) -> bool:
        """
        Send daily performance report
        
        Args:
            stats: Daily performance statistics
            
        Returns:
            bool: True if notification was sent
        """
        try:
            # Send via Discord immediately (not queued)
            if self.discord_notifier:
                await self.discord_notifier.send_performance_report(stats)
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Error sending daily report: {e}")
            return False
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification system statistics"""
        return {
            "discord_enabled": self.discord_notifier is not None,
            "queue_size": self.notification_queue.qsize(),
            "is_running": self.is_running,
            "trade_alerts_enabled": self.config.enable_trade_alerts,
            "error_alerts_enabled": self.config.enable_error_alerts
        }
