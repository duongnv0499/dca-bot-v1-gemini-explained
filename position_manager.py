"""
Position Management Module
Tracks and manages trading positions
"""

from typing import Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Position:
    """Represents a trading position"""
    
    def __init__(self, position_data: Dict):
        """
        Initialize position from exchange data
        
        Args:
            position_data: Position data from exchange
        """
        self.symbol = position_data.get('symbol', '')
        self.side = 'LONG' if position_data.get('side', '') == 'long' else 'SHORT'
        self.contracts = abs(float(position_data.get('contracts', 0)))
        self.entry_price = float(position_data.get('entryPrice', 0))
        self.mark_price = float(position_data.get('markPrice', 0))
        self.unrealized_pnl = float(position_data.get('unrealizedPnl', 0))
        self.percentage = float(position_data.get('percentage', 0))
        self.layers = 1  # Track pyramiding layers
        self.partial_tp_taken = False  # Track if partial TP was taken
        self.stop_loss_price = None  # Current stop loss price
        self.stop_loss_order_id = None  # Stop loss order ID
        
    def update(self, position_data: Dict):
        """Update position with latest data"""
        self.mark_price = float(position_data.get('markPrice', self.mark_price))
        self.unrealized_pnl = float(position_data.get('unrealizedPnl', 0))
        self.percentage = float(position_data.get('percentage', 0))
    
    def to_dict(self) -> Dict:
        """Convert position to dictionary"""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'contracts': self.contracts,
            'entry_price': self.entry_price,
            'mark_price': self.mark_price,
            'unrealized_pnl': self.unrealized_pnl,
            'percentage': self.percentage,
            'layers': self.layers,
            'partial_tp_taken': self.partial_tp_taken,
            'stop_loss_price': self.stop_loss_price
        }


class PositionManager:
    """Manages trading positions"""
    
    def __init__(self, exchange_manager):
        """
        Initialize position manager
        
        Args:
            exchange_manager: ExchangeManager instance
        """
        self.exchange = exchange_manager
        self.current_position: Optional[Position] = None
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
    
    def update_daily_pnl(self):
        """Reset daily PnL if new day"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = current_date
    
    def sync_position(self, symbol: str) -> bool:
        """
        Sync position from exchange
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if position exists, False otherwise
        """
        try:
            positions = self.exchange.fetch_positions(symbol)
            
            if not positions or len(positions) == 0:
                self.current_position = None
                return False
            
            # Get the first open position
            pos_data = positions[0]
            
            if self.current_position is None:
                # Create new position
                self.current_position = Position(pos_data)
                logger.info(f"New position opened: {self.current_position.side} "
                          f"{self.current_position.contracts} @ {self.current_position.entry_price}")
            else:
                # Update existing position
                self.current_position.update(pos_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error syncing position: {str(e)}")
            return False
    
    def has_open_position(self) -> bool:
        """Check if there's an open position"""
        return self.current_position is not None
    
    def get_current_position(self) -> Optional[Position]:
        """Get current position"""
        return self.current_position
    
    def add_layer(self, amount: float):
        """Add a pyramiding layer"""
        if self.current_position:
            self.current_position.layers += 1
            self.current_position.contracts += amount
            logger.info(f"Added layer {self.current_position.layers}, total contracts: {self.current_position.contracts}")
    
    def mark_partial_tp_taken(self):
        """Mark that partial TP was taken"""
        if self.current_position:
            self.current_position.partial_tp_taken = True
            logger.info("Partial TP taken, moved SL to breakeven")
    
    def update_stop_loss(self, price: float, order_id: Optional[str] = None):
        """Update stop loss price"""
        if self.current_position:
            self.current_position.stop_loss_price = price
            if order_id:
                self.current_position.stop_loss_order_id = order_id
            logger.info(f"Stop loss updated to {price}")
    
    def close_position(self, percentage: float = 100.0, reason: str = "") -> bool:
        """
        Close position (or part of it)
        
        Args:
            percentage: Percentage to close (100 = close all)
            reason: Reason for closing
            
        Returns:
            True if successful, False otherwise
        """
        if not self.current_position:
            logger.warning("No position to close")
            return False
        
        try:
            symbol = self.current_position.symbol
            side = 'sell' if self.current_position.side == 'LONG' else 'buy'
            
            if percentage >= 100.0:
                # Close entire position
                amount = self.current_position.contracts
                success = self.exchange.close_position(symbol, side, amount)
                
                if success:
                    logger.info(f"Position closed: {reason}")
                    self.current_position = None
                    return True
            else:
                # Close partial position
                amount = self.current_position.contracts * (percentage / 100.0)
                success = self.exchange.close_position(symbol, side, amount)
                
                if success:
                    # Update position
                    self.current_position.contracts -= amount
                    logger.info(f"Partial position closed ({percentage}%): {reason}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
            return False
    
    def check_daily_loss_limit(self, max_daily_loss: float, balance: float) -> bool:
        """
        Check if daily loss limit is exceeded
        
        Args:
            max_daily_loss: Maximum daily loss percentage
            balance: Current account balance
            
        Returns:
            True if limit exceeded, False otherwise
        """
        self.update_daily_pnl()
        
        if self.current_position:
            # Update daily PnL with unrealized PnL
            current_daily_pnl = self.daily_pnl + self.current_position.unrealized_pnl
        else:
            current_daily_pnl = self.daily_pnl
        
        loss_percentage = abs(current_daily_pnl) / balance if balance > 0 else 0
        
        if loss_percentage >= max_daily_loss:
            logger.warning(f"Daily loss limit exceeded: {loss_percentage:.2%} >= {max_daily_loss:.2%}")
            return True
        
        return False

