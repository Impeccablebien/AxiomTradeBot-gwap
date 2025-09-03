"""
Risk Manager for AxiomTradingBot
Implements risk management rules and position sizing
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..core.base_strategy import TradeSignal
from ..core.config_manager import RiskManagementConfig

@dataclass
class RiskMetrics:
    """Risk metrics for portfolio"""
    total_portfolio_value: float = 0.0
    total_position_value: float = 0.0
    daily_pnl: float = 0.0
    max_drawdown: float = 0.0
    var_95: float = 0.0  # Value at Risk 95%
    portfolio_beta: float = 1.0
    concentration_risk: float = 0.0

class RiskManager:
    """
    Manages risk for the trading bot
    """
    
    def __init__(self, config: RiskManagementConfig):
        """
        Initialize RiskManager
        
        Args:
            config: Risk management configuration
        """
        self.config = config
        self.logger = logging.getLogger("RiskManager")
        
        # Risk state
        self.daily_loss = 0.0
        self.max_drawdown = 0.0
        self.risk_metrics = RiskMetrics()
        self.position_limits: Dict[str, float] = {}
        
        # Risk rules
        self.emergency_stop_triggered = False
        self.daily_limit_reached = False
        
        self.logger.info("RiskManager initialized")
    
    async def can_execute_trade(self, signal: TradeSignal) -> bool:
        """
        Check if a trade can be executed based on risk rules
        
        Args:
            signal: TradeSignal to evaluate
            
        Returns:
            bool: True if trade is allowed
        """
        try:
            # Check emergency stop
            if self.emergency_stop_triggered:
                self.logger.warning("Trade blocked: Emergency stop is active")
                return False
            
            # Check daily loss limit
            if self.daily_limit_reached:
                self.logger.warning("Trade blocked: Daily loss limit reached")
                return False
            
            # Check position size limits
            if not await self._check_position_size_limit(signal):
                return False
            
            # Check portfolio concentration
            if not await self._check_concentration_limit(signal):
                return False
            
            # Check maximum positions
            if not await self._check_max_positions(signal):
                return False
            
            # Check correlation limits
            if not await self._check_correlation_limit(signal):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in risk check: {e}")
            return False  # Fail safe - block trade on error
    
    async def _check_position_size_limit(self, signal: TradeSignal) -> bool:
        """Check if position size is within limits"""
        try:
            if signal.action != "buy":
                return True  # No size limits on sells
            
            # Check against maximum position size
            if signal.amount > self.config.max_position_risk:
                self.logger.warning(f"Position size too large: {signal.amount} > {self.config.max_position_risk}")
                return False
            
            # Check against token-specific limits
            token_limit = self.position_limits.get(signal.token_address)
            if token_limit and signal.amount > token_limit:
                self.logger.warning(f"Token position limit exceeded: {signal.amount} > {token_limit}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking position size: {e}")
            return False
    
    async def _check_concentration_limit(self, signal: TradeSignal) -> bool:
        """Check portfolio concentration limits"""
        try:
            if signal.action != "buy":
                return True
            
            # Calculate what percentage this position would be of total portfolio
            # This is a simplified version - in practice you'd get actual portfolio value
            estimated_portfolio_value = 10.0  # Placeholder - should be actual portfolio value
            position_percentage = (signal.amount / estimated_portfolio_value) * 100
            
            if position_percentage > (self.config.max_position_risk * 100):
                self.logger.warning(f"Position would exceed concentration limit: {position_percentage:.1f}%")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking concentration: {e}")
            return False
    
    async def _check_max_positions(self, signal: TradeSignal) -> bool:
        """Check maximum number of positions"""
        try:
            if signal.action != "buy":
                return True
            
            # Get current number of open positions
            # This would typically come from the database
            current_positions = 0  # Placeholder
            max_positions = 10  # Configurable
            
            if current_positions >= max_positions:
                self.logger.warning(f"Maximum positions reached: {current_positions}/{max_positions}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking max positions: {e}")
            return False
    
    async def _check_correlation_limit(self, signal: TradeSignal) -> bool:
        """Check correlation limits between positions"""
        try:
            # This is a placeholder for correlation analysis
            # In practice, you would analyze correlation between tokens
            # and prevent over-concentration in correlated assets
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking correlation: {e}")
            return False
    
    async def update_daily_pnl(self, pnl: float):
        """Update daily PnL and check limits"""
        try:
            self.daily_loss = min(self.daily_loss, pnl)  # Track worst daily loss
            
            # Check daily loss limit
            if self.daily_loss < -self.config.max_daily_loss:
                self.daily_limit_reached = True
                self.logger.error(f"Daily loss limit exceeded: {self.daily_loss} < -{self.config.max_daily_loss}")
            
            # Check emergency stop loss
            loss_percentage = abs(self.daily_loss) / self.config.max_daily_loss * 100
            if loss_percentage > self.config.emergency_stop_loss:
                self.emergency_stop_triggered = True
                self.logger.error(f"Emergency stop triggered: {loss_percentage:.1f}% loss")
                
        except Exception as e:
            self.logger.error(f"Error updating daily PnL: {e}")
    
    def reset_daily_limits(self):
        """Reset daily limits (call at start of new day)"""
        self.daily_loss = 0.0
        self.daily_limit_reached = False
        self.logger.info("Daily risk limits reset")
    
    def trigger_emergency_stop(self, reason: str = "Manual trigger"):
        """Manually trigger emergency stop"""
        self.emergency_stop_triggered = True
        self.logger.error(f"Emergency stop triggered: {reason}")
    
    def reset_emergency_stop(self):
        """Reset emergency stop (use with caution)"""
        self.emergency_stop_triggered = False
        self.logger.info("Emergency stop reset")
    
    def set_token_limit(self, token_address: str, limit: float):
        """Set position size limit for specific token"""
        self.position_limits[token_address] = limit
        self.logger.info(f"Set position limit for {token_address}: {limit}")
    
    def remove_token_limit(self, token_address: str):
        """Remove position size limit for specific token"""
        if token_address in self.position_limits:
            del self.position_limits[token_address]
            self.logger.info(f"Removed position limit for {token_address}")
    
    async def calculate_position_size(self, signal: TradeSignal, portfolio_value: float) -> float:
        """
        Calculate optimal position size based on risk parameters
        
        Args:
            signal: TradeSignal to size
            portfolio_value: Current portfolio value
            
        Returns:
            float: Recommended position size
        """
        try:
            # Kelly Criterion-based position sizing
            # This is a simplified version
            
            # Base position size as percentage of portfolio
            base_size = portfolio_value * self.config.max_position_risk
            
            # Adjust based on signal confidence
            confidence_multiplier = signal.confidence if hasattr(signal, 'confidence') else 1.0
            adjusted_size = base_size * confidence_multiplier
            
            # Apply absolute limits
            max_size = min(adjusted_size, self.config.max_daily_loss)
            
            # Apply token-specific limits
            token_limit = self.position_limits.get(signal.token_address)
            if token_limit:
                max_size = min(max_size, token_limit)
            
            return max(0.0, min(max_size, signal.amount))
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk status"""
        return {
            "emergency_stop_triggered": self.emergency_stop_triggered,
            "daily_limit_reached": self.daily_limit_reached,
            "daily_loss": self.daily_loss,
            "max_drawdown": self.max_drawdown,
            "position_limits": len(self.position_limits),
            "risk_metrics": {
                "total_portfolio_value": self.risk_metrics.total_portfolio_value,
                "total_position_value": self.risk_metrics.total_position_value,
                "daily_pnl": self.risk_metrics.daily_pnl,
                "max_drawdown": self.risk_metrics.max_drawdown,
                "concentration_risk": self.risk_metrics.concentration_risk
            }
        }
    
    async def update_risk_metrics(self, portfolio_data: Dict[str, Any]):
        """Update risk metrics with current portfolio data"""
        try:
            self.risk_metrics.total_portfolio_value = portfolio_data.get('total_value', 0.0)
            self.risk_metrics.total_position_value = portfolio_data.get('position_value', 0.0)
            self.risk_metrics.daily_pnl = portfolio_data.get('daily_pnl', 0.0)
            
            # Calculate concentration risk
            if self.risk_metrics.total_portfolio_value > 0:
                self.risk_metrics.concentration_risk = (
                    self.risk_metrics.total_position_value / 
                    self.risk_metrics.total_portfolio_value
                )
            
            # Update max drawdown
            current_drawdown = portfolio_data.get('drawdown', 0.0)
            self.risk_metrics.max_drawdown = max(self.risk_metrics.max_drawdown, current_drawdown)
            
            # Update daily PnL for risk checking
            await self.update_daily_pnl(self.risk_metrics.daily_pnl)
            
        except Exception as e:
            self.logger.error(f"Error updating risk metrics: {e}")
    
    def get_risk_recommendations(self) -> List[str]:
        """Get risk management recommendations"""
        recommendations = []
        
        try:
            # Check concentration
            if self.risk_metrics.concentration_risk > 0.8:
                recommendations.append("Consider reducing position concentration")
            
            # Check drawdown
            if self.risk_metrics.max_drawdown > 0.2:
                recommendations.append("High drawdown detected - consider reducing position sizes")
            
            # Check daily loss
            if self.daily_loss < -self.config.max_daily_loss * 0.5:
                recommendations.append("Approaching daily loss limit - consider pausing trading")
            
            # Check portfolio utilization
            if self.risk_metrics.concentration_risk < 0.2:
                recommendations.append("Low portfolio utilization - consider increasing position sizes")
                
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
        
        return recommendations
