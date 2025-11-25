"""
Exchange Interface Module
Handles connection and trading operations with Binance via CCXT
"""

import ccxt
import pandas as pd
import time
from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ExchangeManager:
    """Manages exchange connection and trading operations"""
    
    def __init__(self, api_key: str, secret_key: str, testnet: bool = False):
        """
        Initialize exchange connection
        
        Args:
            api_key: Binance API key
            secret_key: Binance secret key
            testnet: Use testnet if True
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        
        # Initialize exchange
        try:
            exchange_class = getattr(ccxt, 'binanceusdm')
            self.exchange = exchange_class({
                'apiKey': api_key,
                'secret': secret_key,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # Use futures
                }
            })
            
            # Set testnet if needed
            if testnet:
                self.exchange.set_sandbox_mode(True)
            
            # Load markets
            self.exchange.load_markets()
            logger.info(f"Exchange initialized: {self.exchange.id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {str(e)}")
            raise
    
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set leverage for a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'ETH/USDT:USDT')
            leverage: Leverage value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # For Binance USD-M futures, use set_leverage
            self.exchange.set_leverage(leverage, symbol)
            logger.info(f"Leverage set to {leverage}x for {symbol}")
            return True
        except ccxt.NetworkError as e:
            logger.error(f"Network error setting leverage: {str(e)}")
            return False
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error setting leverage: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting leverage: {str(e)}")
            return False
    
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV (candlestick) data
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (e.g., '1h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            DataFrame with OHLCV data or None if error
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv or len(ohlcv) == 0:
                logger.warning(f"No OHLCV data returned for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching OHLCV: {str(e)}")
            return None
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching OHLCV: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching OHLCV: {str(e)}")
            return None
    
    def fetch_balance(self) -> Optional[Dict]:
        """
        Fetch account balance
        
        Returns:
            Balance dictionary or None if error
        """
        try:
            balance = self.exchange.fetch_balance()
            return balance
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching balance: {str(e)}")
            return None
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching balance: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching balance: {str(e)}")
            return None
    
    def get_usdt_balance(self) -> Optional[float]:
        """
        Get USDT balance from account
        
        Returns:
            USDT balance or None if error
        """
        try:
            balance = self.fetch_balance()
            if balance is None:
                return None
            
            # For futures, check 'USDT' in total
            if 'USDT' in balance.get('total', {}):
                return float(balance['total']['USDT'])
            elif 'USDT' in balance:
                return float(balance['USDT'])
            else:
                logger.warning("USDT balance not found")
                return 0.0
        except Exception as e:
            logger.error(f"Error getting USDT balance: {str(e)}")
            return None
    
    def fetch_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Fetch open positions
        
        Args:
            symbol: Optional symbol to filter positions
            
        Returns:
            List of position dictionaries
        """
        try:
            positions = self.exchange.fetch_positions(symbols=[symbol] if symbol else None)
            
            # Filter only open positions (contracts > 0)
            open_positions = []
            for pos in positions:
                if pos.get('contracts', 0) != 0:
                    open_positions.append(pos)
            
            return open_positions
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching positions: {str(e)}")
            return []
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching positions: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching positions: {str(e)}")
            return []
    
    def create_market_order(self, symbol: str, side: str, amount: float) -> Optional[Dict]:
        """
        Create a market order
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            amount: Order amount (in base currency)
            
        Returns:
            Order dictionary or None if error
        """
        try:
            order = self.exchange.create_market_order(symbol, side, amount)
            logger.info(f"Market order created: {side} {amount} {symbol}")
            return order
        except ccxt.NetworkError as e:
            logger.error(f"Network error creating market order: {str(e)}")
            return None
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error creating market order: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating market order: {str(e)}")
            return None
    
    def create_stop_loss_order(self, symbol: str, side: str, amount: float, stop_price: float) -> Optional[Dict]:
        """
        Create a stop loss order
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell' (opposite of position side)
            amount: Order amount
            stop_price: Stop loss price
            
        Returns:
            Order dictionary or None if error
        """
        try:
            # For Binance futures, use STOP_MARKET order type
            # Note: stopPrice parameter format may vary, using params for safety
            order = self.exchange.create_order(
                symbol=symbol,
                type='STOP_MARKET',
                side=side,
                amount=amount,
                params={
                    'stopPrice': stop_price,
                    'reduceOnly': True,  # Only reduce position, not open new
                    'closePosition': False  # Don't close entire position
                }
            )
            logger.info(f"Stop loss order created: {side} {amount} {symbol} at {stop_price}")
            return order
        except ccxt.NetworkError as e:
            logger.error(f"Network error creating stop loss: {str(e)}")
            return None
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error creating stop loss: {str(e)}")
            # Try alternative method if STOP_MARKET fails
            try:
                # Alternative: Use stopPrice directly in params
                order = self.exchange.create_order(
                    symbol=symbol,
                    type='MARKET',
                    side=side,
                    amount=amount,
                    params={
                        'stopPrice': stop_price,
                        'reduceOnly': True
                    }
                )
                logger.info(f"Stop loss order created (alternative method): {side} {amount} {symbol} at {stop_price}")
                return order
            except Exception as e2:
                logger.error(f"Alternative stop loss method also failed: {str(e2)}")
                return None
        except Exception as e:
            logger.error(f"Unexpected error creating stop loss: {str(e)}")
            return None
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            symbol: Trading symbol
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Order {order_id} cancelled")
            return True
        except ccxt.NetworkError as e:
            logger.error(f"Network error cancelling order: {str(e)}")
            return False
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error cancelling order: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error cancelling order: {str(e)}")
            return False
    
    def close_position(self, symbol: str, side: str, amount: Optional[float] = None) -> bool:
        """
        Close a position (or part of it)
        
        Args:
            symbol: Trading symbol
            side: 'buy' to close short, 'sell' to close long
            amount: Amount to close (None = close all)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if amount is None:
                # Close entire position
                positions = self.fetch_positions(symbol)
                if not positions:
                    logger.warning(f"No open position found for {symbol}")
                    return False
                
                pos = positions[0]
                amount = abs(pos.get('contracts', 0))
            
            if amount <= 0:
                logger.warning(f"Invalid amount to close: {amount}")
                return False
            
            # Create market order to close
            order = self.create_market_order(symbol, side, amount)
            return order is not None
            
        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
            return False

