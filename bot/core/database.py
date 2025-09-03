"""
Database Manager for AxiomTradingBot
Handles persistent storage of trades, positions, and analytics
"""

import sqlite3
import logging
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class TradeRecord:
    """Database record for a trade"""
    id: Optional[int] = None
    strategy_name: str = ""
    token_address: str = ""
    action: str = ""  # buy/sell
    amount: float = 0.0
    price: float = 0.0
    timestamp: datetime = None
    tx_hash: str = ""
    gas_used: float = 0.0
    success: bool = True
    error_message: str = ""
    metadata: Dict[str, Any] = None

@dataclass
class PositionRecord:
    """Database record for a position"""
    id: Optional[int] = None
    strategy_name: str = ""
    token_address: str = ""
    entry_price: float = 0.0
    current_price: float = 0.0
    amount: float = 0.0
    entry_time: datetime = None
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    realized_pnl: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    status: str = "open"  # open/closed/partial
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None

class DatabaseManager:
    """
    Manages database operations for the trading bot
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize DatabaseManager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.logger = logging.getLogger("DatabaseManager")
        
        if db_path is None:
            db_path = Path("data") / "trading_bot.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize database tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    token_address TEXT NOT NULL,
                    action TEXT NOT NULL,
                    amount REAL NOT NULL,
                    price REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    tx_hash TEXT,
                    gas_used REAL DEFAULT 0,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    metadata TEXT
                )
            ''')
            
            # Create positions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    token_address TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    amount REAL NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    exit_price REAL,
                    realized_pnl REAL,
                    unrealized_pnl REAL,
                    status TEXT DEFAULT 'open',
                    take_profit REAL,
                    stop_loss REAL
                )
            ''')
            
            # Create performance tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_performance (
                    date TEXT PRIMARY KEY,
                    strategy_name TEXT NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    total_volume REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    portfolio_value REAL DEFAULT 0
                )
            ''')
            
            # Create tokens table for tracking discovered tokens
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tokens (
                    address TEXT PRIMARY KEY,
                    symbol TEXT,
                    name TEXT,
                    decimals INTEGER,
                    first_seen TEXT NOT NULL,
                    liquidity REAL DEFAULT 0,
                    market_cap REAL DEFAULT 0,
                    buy_tax REAL DEFAULT 0,
                    sell_tax REAL DEFAULT 0,
                    is_blacklisted BOOLEAN DEFAULT 0,
                    metadata TEXT
                )
            ''')
            
            # Create wallet tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tracked_wallets (
                    address TEXT PRIMARY KEY,
                    name TEXT,
                    added_date TEXT NOT NULL,
                    last_activity TEXT,
                    total_profit REAL DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    metadata TEXT
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_strategy ON positions(strategy_name)')
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    async def record_trade(self, trade: TradeRecord) -> int:
        """
        Record a trade in the database
        
        Args:
            trade: TradeRecord to store
            
        Returns:
            int: ID of the inserted record
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trades (
                    strategy_name, token_address, action, amount, price,
                    timestamp, tx_hash, gas_used, success, error_message, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade.strategy_name,
                trade.token_address,
                trade.action,
                trade.amount,
                trade.price,
                trade.timestamp.isoformat() if trade.timestamp else datetime.utcnow().isoformat(),
                trade.tx_hash,
                trade.gas_used,
                trade.success,
                trade.error_message,
                json.dumps(trade.metadata) if trade.metadata else None
            ))
            
            trade_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Recorded trade {trade_id}: {trade.action} {trade.amount} {trade.token_address}")
            return trade_id
            
        except Exception as e:
            self.logger.error(f"Error recording trade: {e}")
            raise
    
    async def record_position(self, position: PositionRecord) -> int:
        """
        Record a position in the database
        
        Args:
            position: PositionRecord to store
            
        Returns:
            int: ID of the inserted record
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO positions (
                    strategy_name, token_address, entry_price, current_price, amount,
                    entry_time, exit_time, exit_price, realized_pnl, unrealized_pnl,
                    status, take_profit, stop_loss
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                position.strategy_name,
                position.token_address,
                position.entry_price,
                position.current_price,
                position.amount,
                position.entry_time.isoformat() if position.entry_time else datetime.utcnow().isoformat(),
                position.exit_time.isoformat() if position.exit_time else None,
                position.exit_price,
                position.realized_pnl,
                position.unrealized_pnl,
                position.status,
                position.take_profit,
                position.stop_loss
            ))
            
            position_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Recorded position {position_id}: {position.token_address}")
            return position_id
            
        except Exception as e:
            self.logger.error(f"Error recording position: {e}")
            raise
    
    async def update_position(self, position_id: int, **kwargs):
        """
        Update a position in the database
        
        Args:
            position_id: ID of position to update
            **kwargs: Fields to update
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build dynamic update query
            set_clauses = []
            values = []
            
            for field, value in kwargs.items():
                if field in ['current_price', 'exit_price', 'realized_pnl', 'unrealized_pnl', 'status']:
                    set_clauses.append(f"{field} = ?")
                    if field == 'exit_time' and value:
                        values.append(value.isoformat())
                    else:
                        values.append(value)
            
            if set_clauses:
                query = f"UPDATE positions SET {', '.join(set_clauses)} WHERE id = ?"
                values.append(position_id)
                
                cursor.execute(query, values)
                conn.commit()
                
                self.logger.debug(f"Updated position {position_id}")
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error updating position: {e}")
            raise
    
    async def get_open_positions(self, strategy_name: str = None) -> List[PositionRecord]:
        """
        Get all open positions
        
        Args:
            strategy_name: Optional strategy filter
            
        Returns:
            List of PositionRecord objects
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if strategy_name:
                cursor.execute('''
                    SELECT * FROM positions 
                    WHERE status = 'open' AND strategy_name = ?
                    ORDER BY entry_time DESC
                ''', (strategy_name,))
            else:
                cursor.execute('''
                    SELECT * FROM positions 
                    WHERE status = 'open'
                    ORDER BY entry_time DESC
                ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            positions = []
            for row in rows:
                position = PositionRecord(
                    id=row[0],
                    strategy_name=row[1],
                    token_address=row[2],
                    entry_price=row[3],
                    current_price=row[4],
                    amount=row[5],
                    entry_time=datetime.fromisoformat(row[6]),
                    exit_time=datetime.fromisoformat(row[7]) if row[7] else None,
                    exit_price=row[8],
                    realized_pnl=row[9],
                    unrealized_pnl=row[10],
                    status=row[11],
                    take_profit=row[12],
                    stop_loss=row[13]
                )
                positions.append(position)
            
            return positions
            
        except Exception as e:
            self.logger.error(f"Error getting open positions: {e}")
            return []
    
    async def get_trade_history(self, strategy_name: str = None, days: int = 30) -> List[TradeRecord]:
        """
        Get trade history
        
        Args:
            strategy_name: Optional strategy filter
            days: Number of days to look back
            
        Returns:
            List of TradeRecord objects
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            if strategy_name:
                cursor.execute('''
                    SELECT * FROM trades 
                    WHERE timestamp >= ? AND strategy_name = ?
                    ORDER BY timestamp DESC
                ''', (start_date, strategy_name))
            else:
                cursor.execute('''
                    SELECT * FROM trades 
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                ''', (start_date,))
            
            rows = cursor.fetchall()
            conn.close()
            
            trades = []
            for row in rows:
                trade = TradeRecord(
                    id=row[0],
                    strategy_name=row[1],
                    token_address=row[2],
                    action=row[3],
                    amount=row[4],
                    price=row[5],
                    timestamp=datetime.fromisoformat(row[6]),
                    tx_hash=row[7] or "",
                    gas_used=row[8],
                    success=bool(row[9]),
                    error_message=row[10] or "",
                    metadata=json.loads(row[11]) if row[11] else {}
                )
                trades.append(trade)
            
            return trades
            
        except Exception as e:
            self.logger.error(f"Error getting trade history: {e}")
            return []
    
    async def get_performance_stats(self, strategy_name: str = None, days: int = 30) -> Dict[str, Any]:
        """
        Get performance statistics
        
        Args:
            strategy_name: Optional strategy filter
            days: Number of days to analyze
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            trades = await self.get_trade_history(strategy_name, days)
            positions = await self.get_open_positions(strategy_name)
            
            if not trades:
                return {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "average_trade": 0.0,
                    "total_volume": 0.0,
                    "open_positions": len(positions)
                }
            
            # Calculate statistics
            buy_trades = [t for t in trades if t.action == 'buy' and t.success]
            sell_trades = [t for t in trades if t.action == 'sell' and t.success]
            
            total_volume = sum(t.amount * t.price for t in trades if t.success)
            
            # Calculate PnL from matched buy/sell pairs
            total_pnl = 0.0
            winning_trades = 0
            
            # Group trades by token
            token_trades = {}
            for trade in trades:
                if trade.token_address not in token_trades:
                    token_trades[trade.token_address] = []
                token_trades[trade.token_address].append(trade)
            
            # Calculate PnL for each token
            for token_address, token_trade_list in token_trades.items():
                token_trade_list.sort(key=lambda x: x.timestamp)
                
                position_amount = 0.0
                position_cost = 0.0
                
                for trade in token_trade_list:
                    if not trade.success:
                        continue
                        
                    if trade.action == 'buy':
                        position_amount += trade.amount
                        position_cost += trade.amount * trade.price
                    elif trade.action == 'sell' and position_amount > 0:
                        sell_ratio = min(trade.amount / position_amount, 1.0)
                        sell_cost = position_cost * sell_ratio
                        sell_revenue = trade.amount * trade.price
                        
                        pnl = sell_revenue - sell_cost
                        total_pnl += pnl
                        
                        if pnl > 0:
                            winning_trades += 1
                        
                        # Update position
                        position_amount -= trade.amount
                        position_cost -= sell_cost
            
            # Calculate unrealized PnL from open positions
            unrealized_pnl = sum(p.unrealized_pnl or 0 for p in positions)
            
            total_completed_trades = len([t for t in trades if t.action == 'sell'])
            win_rate = (winning_trades / total_completed_trades * 100) if total_completed_trades > 0 else 0
            
            return {
                "total_trades": len(trades),
                "completed_trades": total_completed_trades,
                "winning_trades": winning_trades,
                "win_rate": win_rate,
                "total_pnl": total_pnl,
                "unrealized_pnl": unrealized_pnl,
                "total_pnl_including_unrealized": total_pnl + unrealized_pnl,
                "average_trade": total_pnl / total_completed_trades if total_completed_trades > 0 else 0,
                "total_volume": total_volume,
                "open_positions": len(positions)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating performance stats: {e}")
            return {}
    
    async def add_token(self, token_data: Dict[str, Any]):
        """Add a new token to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO tokens (
                    address, symbol, name, decimals, first_seen,
                    liquidity, market_cap, buy_tax, sell_tax, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                token_data.get('address', ''),
                token_data.get('symbol', ''),
                token_data.get('name', ''),
                token_data.get('decimals', 9),
                datetime.utcnow().isoformat(),
                token_data.get('liquidity', 0),
                token_data.get('market_cap', 0),
                token_data.get('buy_tax', 0),
                token_data.get('sell_tax', 0),
                json.dumps(token_data.get('metadata', {}))
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Added token {token_data.get('address')} to database")
            
        except Exception as e:
            self.logger.error(f"Error adding token: {e}")
    
    async def cleanup_old_data(self, days: int = 90):
        """
        Clean up old data from the database
        
        Args:
            days: Keep data newer than this many days
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Clean old trades
            cursor.execute('DELETE FROM trades WHERE timestamp < ?', (cutoff_date,))
            
            # Clean old closed positions
            cursor.execute('''
                DELETE FROM positions 
                WHERE status = 'closed' AND exit_time < ?
            ''', (cutoff_date,))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Cleaned up data older than {days} days")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
