"""
Discord Notifier for AxiomTradingBot
Sends notifications to Discord via webhooks
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

class DiscordNotifier:
    """
    Handles Discord notifications via webhooks
    """
    
    def __init__(self, webhook_url: str, bot_name: str = "AxiomTradingBot"):
        """
        Initialize Discord notifier
        
        Args:
            webhook_url: Discord webhook URL
            bot_name: Name to display for the bot
        """
        self.webhook_url = webhook_url
        self.bot_name = bot_name
        self.logger = logging.getLogger("DiscordNotifier")
        
        # Rate limiting
        self.last_message_time = 0
        self.min_interval = 1.0  # Minimum seconds between messages
        
    async def send_message(self, content: str, embed: Dict[str, Any] = None) -> bool:
        """
        Send a message to Discord
        
        Args:
            content: Text content of the message
            embed: Discord embed object (optional)
            
        Returns:
            bool: True if message was sent successfully
        """
        try:
            # Rate limiting
            current_time = asyncio.get_event_loop().time()
            if current_time - self.last_message_time < self.min_interval:
                await asyncio.sleep(self.min_interval - (current_time - self.last_message_time))
            
            payload = {
                "username": self.bot_name,
                "content": content
            }
            
            if embed:
                payload["embeds"] = [embed]
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status in [200, 204]:
                        self.last_message_time = asyncio.get_event_loop().time()
                        return True
                    else:
                        self.logger.error(f"Discord webhook error: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Error sending Discord message: {e}")
            return False
    
    async def send_trade_notification(self, action: str, token_address: str, 
                                    amount: float, price: float, success: bool,
                                    tx_hash: str = "", reason: str = "") -> bool:
        """
        Send a trade notification
        
        Args:
            action: 'buy' or 'sell'
            token_address: Token contract address
            amount: Trade amount
            price: Trade price
            success: Whether trade was successful
            tx_hash: Transaction hash
            reason: Reason for the trade
            
        Returns:
            bool: True if notification was sent
        """
        try:
            # Choose emoji based on action and success
            if success:
                emoji = "✅" if action == "buy" else "💰"
                color = 0x00ff00 if action == "buy" else 0x0099ff
                status = "Successful"
            else:
                emoji = "❌"
                color = 0xff0000
                status = "Failed"
            
            # Create embed
            embed = {
                "title": f"{emoji} {action.upper()} Trade {status}",
                "color": color,
                "fields": [
                    {
                        "name": "Token",
                        "value": f"`{token_address[:8]}...{token_address[-8:]}`",
                        "inline": True
                    },
                    {
                        "name": "Amount",
                        "value": f"{amount:.6f} SOL",
                        "inline": True
                    },
                    {
                        "name": "Price",
                        "value": f"{price:.8f}" if price > 0 else "N/A",
                        "inline": True
                    }
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if reason:
                embed["fields"].append({
                    "name": "Reason",
                    "value": reason,
                    "inline": False
                })
            
            if tx_hash:
                embed["fields"].append({
                    "name": "Transaction",
                    "value": f"[View on Solscan](https://solscan.io/tx/{tx_hash})",
                    "inline": False
                })
            
            content = f"{emoji} **{action.upper()}** trade {status.lower()}"
            
            return await self.send_message(content, embed)
            
        except Exception as e:
            self.logger.error(f"Error sending trade notification: {e}")
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
            bool: True if notification was sent
        """
        try:
            if action == "opened":
                emoji = "🎯"
                color = 0x00ff00
                title = "Position Opened"
            else:  # closed
                if pnl is not None and pnl > 0:
                    emoji = "💰"
                    color = 0x00ff00
                else:
                    emoji = "📉"
                    color = 0xff0000
                title = "Position Closed"
            
            embed = {
                "title": f"{emoji} {title}",
                "color": color,
                "fields": [
                    {
                        "name": "Token",
                        "value": f"`{token_address[:8]}...{token_address[-8:]}`",
                        "inline": True
                    },
                    {
                        "name": "Amount",
                        "value": f"{amount:.6f} SOL",
                        "inline": True
                    },
                    {
                        "name": "Entry Price",
                        "value": f"{entry_price:.8f}",
                        "inline": True
                    }
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if current_price is not None:
                embed["fields"].append({
                    "name": "Exit Price",
                    "value": f"{current_price:.8f}",
                    "inline": True
                })
            
            if pnl is not None:
                pnl_emoji = "📈" if pnl > 0 else "📉"
                embed["fields"].append({
                    "name": "P&L",
                    "value": f"{pnl_emoji} {pnl:.6f} SOL",
                    "inline": True
                })
                
                # Calculate percentage
                if entry_price > 0:
                    pnl_percent = (pnl / (amount * entry_price)) * 100
                    embed["fields"].append({
                        "name": "P&L %",
                        "value": f"{pnl_percent:+.2f}%",
                        "inline": True
                    })
            
            content = f"{emoji} Position {action}"
            
            return await self.send_message(content, embed)
            
        except Exception as e:
            self.logger.error(f"Error sending position notification: {e}")
            return False
    
    async def send_bot_notification(self, title: str, message: str, 
                                   notification_type: str = "info") -> bool:
        """
        Send a bot status notification
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: 'info', 'warning', 'error', 'success'
            
        Returns:
            bool: True if notification was sent
        """
        try:
            # Choose emoji and color based on type
            type_config = {
                "info": {"emoji": "ℹ️", "color": 0x0099ff},
                "warning": {"emoji": "⚠️", "color": 0xffcc00},
                "error": {"emoji": "🚨", "color": 0xff0000},
                "success": {"emoji": "✅", "color": 0x00ff00}
            }
            
            config = type_config.get(notification_type, type_config["info"])
            
            embed = {
                "title": f"{config['emoji']} {title}",
                "description": message,
                "color": config["color"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            content = f"{config['emoji']} **{title}**"
            
            return await self.send_message(content, embed)
            
        except Exception as e:
            self.logger.error(f"Error sending bot notification: {e}")
            return False
    
    async def send_performance_report(self, stats: Dict[str, Any]) -> bool:
        """
        Send a performance report
        
        Args:
            stats: Performance statistics
            
        Returns:
            bool: True if notification was sent
        """
        try:
            total_pnl = stats.get('total_pnl', 0)
            win_rate = stats.get('win_rate', 0)
            total_trades = stats.get('total_trades', 0)
            
            # Choose emoji based on performance
            if total_pnl > 0:
                emoji = "📈"
                color = 0x00ff00
            elif total_pnl < 0:
                emoji = "📉"
                color = 0xff0000
            else:
                emoji = "➖"
                color = 0x808080
            
            embed = {
                "title": f"{emoji} Performance Report",
                "color": color,
                "fields": [
                    {
                        "name": "Total P&L",
                        "value": f"{total_pnl:+.6f} SOL",
                        "inline": True
                    },
                    {
                        "name": "Win Rate",
                        "value": f"{win_rate:.1f}%",
                        "inline": True
                    },
                    {
                        "name": "Total Trades",
                        "value": str(total_trades),
                        "inline": True
                    },
                    {
                        "name": "Winning Trades",
                        "value": str(stats.get('winning_trades', 0)),
                        "inline": True
                    },
                    {
                        "name": "Open Positions",
                        "value": str(stats.get('open_positions', 0)),
                        "inline": True
                    },
                    {
                        "name": "Total Volume",
                        "value": f"{stats.get('total_volume', 0):.2f} SOL",
                        "inline": True
                    }
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            content = f"{emoji} **Performance Report**"
            
            return await self.send_message(content, embed)
            
        except Exception as e:
            self.logger.error(f"Error sending performance report: {e}")
            return False
    
    async def send_error_notification(self, error_message: str, details: Dict[str, Any] = None) -> bool:
        """
        Send an error notification
        
        Args:
            error_message: Error message
            details: Additional error details
            
        Returns:
            bool: True if notification was sent
        """
        try:
            embed = {
                "title": "🚨 Error Occurred",
                "description": error_message,
                "color": 0xff0000,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if details:
                embed["fields"] = []
                for key, value in details.items():
                    if len(embed["fields"]) < 10:  # Discord limit
                        embed["fields"].append({
                            "name": key.replace("_", " ").title(),
                            "value": str(value)[:1024],  # Discord field value limit
                            "inline": True
                        })
            
            content = "🚨 **Error Alert**"
            
            return await self.send_message(content, embed)
            
        except Exception as e:
            self.logger.error(f"Error sending error notification: {e}")
            return False
