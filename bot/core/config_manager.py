"""
Configuration Manager for AxiomTradingBot
Handles loading and validation of configuration files
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class AxiomTradeConfig:
    """AxiomTrade API configuration"""
    email: str = ""
    password: str = ""
    base_url: str = "https://api6.axiom.trade"
    
@dataclass  
class TradingConfig:
    """Trading configuration"""
    default_buy_amount: float = 0.1
    max_position_size: float = 1.0
    take_profit_percentage: float = 50.0
    stop_loss_percentage: float = 20.0
    max_positions: int = 10
    min_liquidity: float = 5.0
    max_slippage: float = 5.0

@dataclass
class SnipingConfig:
    """Token sniping configuration"""
    enabled: bool = True
    min_liquidity: float = 5.0
    max_buy_tax: float = 10.0
    max_sell_tax: float = 10.0
    blacklisted_tokens: list = field(default_factory=list)
    whitelisted_tokens: list = field(default_factory=list)
    auto_sell_delay: int = 60  # seconds

@dataclass
class NotificationConfig:
    """Notification configuration"""
    discord_enabled: bool = False
    discord_webhook_url: str = ""
    log_level: str = "INFO"
    enable_trade_alerts: bool = True
    enable_error_alerts: bool = True

@dataclass
class RiskManagementConfig:
    """Risk management configuration"""
    max_daily_loss: float = 1.0  # SOL
    max_position_risk: float = 0.1  # 10% of portfolio
    portfolio_rebalance_threshold: float = 0.2  # 20%
    emergency_stop_loss: float = 50.0  # 50% total loss

@dataclass
class BotConfig:
    """Main bot configuration"""
    axiom_trade: AxiomTradeConfig = field(default_factory=AxiomTradeConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    sniping: SnipingConfig = field(default_factory=SnipingConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    risk_management: RiskManagementConfig = field(default_factory=RiskManagementConfig)

class ConfigManager:
    """
    Manages bot configuration loading and validation
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize ConfigManager
        
        Args:
            config_path: Path to configuration file
        """
        self.logger = logging.getLogger("ConfigManager")
        
        # Default config path
        if config_path is None:
            config_path = os.path.join(os.getcwd(), "config", "config.yaml")
        
        self.config_path = Path(config_path)
        self.config: BotConfig = BotConfig()
        
        # Load configuration
        self.load_config()
        
    def load_config(self):
        """Load configuration from file"""
        try:
            if not self.config_path.exists():
                self.logger.warning(f"Config file not found at {self.config_path}, using defaults")
                self._create_example_config()
                return
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                
            if not config_data:
                self.logger.warning("Empty config file, using defaults")
                return
                
            # Load each section
            self._load_axiom_trade_config(config_data.get('axiom_trade', {}))
            self._load_trading_config(config_data.get('trading', {}))
            self._load_sniping_config(config_data.get('sniping', {}))
            self._load_notification_config(config_data.get('notifications', {}))
            self._load_risk_management_config(config_data.get('risk_management', {}))
            
            self.logger.info(f"Configuration loaded successfully from {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            self.logger.info("Using default configuration")
    
    def _load_axiom_trade_config(self, data: Dict[str, Any]):
        """Load AxiomTrade API configuration"""
        self.config.axiom_trade.email = data.get('email', '')
        self.config.axiom_trade.password = data.get('password', '')
        self.config.axiom_trade.base_url = data.get('base_url', 'https://api6.axiom.trade')
        
    def _load_trading_config(self, data: Dict[str, Any]):
        """Load trading configuration"""
        self.config.trading.default_buy_amount = data.get('default_buy_amount', 0.1)
        self.config.trading.max_position_size = data.get('max_position_size', 1.0)
        self.config.trading.take_profit_percentage = data.get('take_profit_percentage', 50.0)
        self.config.trading.stop_loss_percentage = data.get('stop_loss_percentage', 20.0)
        self.config.trading.max_positions = data.get('max_positions', 10)
        self.config.trading.min_liquidity = data.get('min_liquidity', 5.0)
        self.config.trading.max_slippage = data.get('max_slippage', 5.0)
        
    def _load_sniping_config(self, data: Dict[str, Any]):
        """Load token sniping configuration"""
        self.config.sniping.enabled = data.get('enabled', True)
        self.config.sniping.min_liquidity = data.get('min_liquidity', 5.0)
        self.config.sniping.max_buy_tax = data.get('max_buy_tax', 10.0)
        self.config.sniping.max_sell_tax = data.get('max_sell_tax', 10.0)
        self.config.sniping.blacklisted_tokens = data.get('blacklisted_tokens', [])
        self.config.sniping.whitelisted_tokens = data.get('whitelisted_tokens', [])
        self.config.sniping.auto_sell_delay = data.get('auto_sell_delay', 60)
        
    def _load_notification_config(self, data: Dict[str, Any]):
        """Load notification configuration"""
        discord_config = data.get('discord', {})
        self.config.notifications.discord_enabled = discord_config.get('enabled', False)
        self.config.notifications.discord_webhook_url = discord_config.get('webhook_url', '')
        self.config.notifications.log_level = data.get('log_level', 'INFO')
        self.config.notifications.enable_trade_alerts = data.get('enable_trade_alerts', True)
        self.config.notifications.enable_error_alerts = data.get('enable_error_alerts', True)
        
    def _load_risk_management_config(self, data: Dict[str, Any]):
        """Load risk management configuration"""
        self.config.risk_management.max_daily_loss = data.get('max_daily_loss', 1.0)
        self.config.risk_management.max_position_risk = data.get('max_position_risk', 0.1)
        self.config.risk_management.portfolio_rebalance_threshold = data.get('portfolio_rebalance_threshold', 0.2)
        self.config.risk_management.emergency_stop_loss = data.get('emergency_stop_loss', 50.0)
        
    def _create_example_config(self):
        """Create an example configuration file"""
        example_config = {
            'axiom_trade': {
                'email': 'your-email@example.com',
                'password': 'your-base64-encoded-password',
                'base_url': 'https://api6.axiom.trade'
            },
            'trading': {
                'default_buy_amount': 0.1,
                'max_position_size': 1.0,
                'take_profit_percentage': 50.0,
                'stop_loss_percentage': 20.0,
                'max_positions': 10,
                'min_liquidity': 5.0,
                'max_slippage': 5.0
            },
            'sniping': {
                'enabled': True,
                'min_liquidity': 5.0,
                'max_buy_tax': 10.0,
                'max_sell_tax': 10.0,
                'blacklisted_tokens': [],
                'whitelisted_tokens': [],
                'auto_sell_delay': 60
            },
            'notifications': {
                'discord': {
                    'enabled': False,
                    'webhook_url': 'your-discord-webhook-url'
                },
                'log_level': 'INFO',
                'enable_trade_alerts': True,
                'enable_error_alerts': True
            },
            'risk_management': {
                'max_daily_loss': 1.0,
                'max_position_risk': 0.1,
                'portfolio_rebalance_threshold': 0.2,
                'emergency_stop_loss': 50.0
            }
        }
        
        try:
            # Create config directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            example_path = self.config_path.parent / "config.example.yaml"
            with open(example_path, 'w', encoding='utf-8') as f:
                yaml.dump(example_config, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Created example configuration at {example_path}")
            self.logger.info(f"Copy it to {self.config_path} and edit with your settings")
            
        except Exception as e:
            self.logger.error(f"Error creating example config: {e}")
    
    def validate_config(self) -> bool:
        """
        Validate the configuration
        
        Returns:
            bool: True if configuration is valid
        """
        errors = []
        
        # Validate AxiomTrade credentials
        if not self.config.axiom_trade.email:
            errors.append("AxiomTrade email is required")
        if not self.config.axiom_trade.password:
            errors.append("AxiomTrade password is required")
            
        # Validate trading parameters
        if self.config.trading.default_buy_amount <= 0:
            errors.append("Default buy amount must be positive")
        if self.config.trading.max_position_size <= 0:
            errors.append("Max position size must be positive")
        if self.config.trading.take_profit_percentage <= 0:
            errors.append("Take profit percentage must be positive")
        if self.config.trading.stop_loss_percentage <= 0:
            errors.append("Stop loss percentage must be positive")
            
        # Validate sniping parameters
        if self.config.sniping.min_liquidity < 0:
            errors.append("Minimum liquidity cannot be negative")
        if self.config.sniping.max_buy_tax < 0 or self.config.sniping.max_buy_tax > 100:
            errors.append("Max buy tax must be between 0 and 100")
        if self.config.sniping.max_sell_tax < 0 or self.config.sniping.max_sell_tax > 100:
            errors.append("Max sell tax must be between 0 and 100")
            
        # Validate Discord webhook if enabled
        if self.config.notifications.discord_enabled and not self.config.notifications.discord_webhook_url:
            errors.append("Discord webhook URL is required when Discord notifications are enabled")
            
        if errors:
            for error in errors:
                self.logger.error(f"Configuration error: {error}")
            return False
            
        self.logger.info("Configuration validation passed")
        return True
    
    def get_config(self) -> BotConfig:
        """Get the current configuration"""
        return self.config
    
    def reload_config(self):
        """Reload configuration from file"""
        self.logger.info("Reloading configuration...")
        self.load_config()
        
    def get_strategy_config(self, strategy_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific strategy
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            Dict containing strategy-specific configuration
        """
        if strategy_name.lower() == 'tokensniper':
            return {
                'enabled': self.config.sniping.enabled,
                'buy_amount': self.config.trading.default_buy_amount,
                'min_liquidity': self.config.sniping.min_liquidity,
                'max_buy_tax': self.config.sniping.max_buy_tax,
                'max_sell_tax': self.config.sniping.max_sell_tax,
                'take_profit': self.config.trading.take_profit_percentage,
                'stop_loss': self.config.trading.stop_loss_percentage,
                'blacklisted_tokens': self.config.sniping.blacklisted_tokens,
                'whitelisted_tokens': self.config.sniping.whitelisted_tokens,
                'auto_sell_delay': self.config.sniping.auto_sell_delay
            }
        elif strategy_name.lower() == 'wallettracker':
            return {
                'copy_percentage': 50.0,  # Default to 50% copy
                'min_trade_size': 0.01,
                'max_copy_amount': self.config.trading.max_position_size,
                'take_profit': self.config.trading.take_profit_percentage,
                'stop_loss': self.config.trading.stop_loss_percentage,
                'delay_seconds': 1  # Delay before copying trade
            }
        else:
            # Return general trading config for unknown strategies
            return {
                'buy_amount': self.config.trading.default_buy_amount,
                'max_position_size': self.config.trading.max_position_size,
                'take_profit': self.config.trading.take_profit_percentage,
                'stop_loss': self.config.trading.stop_loss_percentage,
                'min_liquidity': self.config.trading.min_liquidity,
                'max_slippage': self.config.trading.max_slippage
            }
