"""
TITAN-MA7 QUANT SYSTEM (VERSION 2.1 - RSI ENHANCED)
Main trading bot implementation
"""

import os
import time
import logging
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import pandas as pd

from config import *
from exchange import ExchangeManager
from position_manager import PositionManager
from indicators import (
    calculate_ema, calculate_rsi, calculate_atr,
    count_price_ma_crosses, calculate_slope, calculate_deviation
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot class"""
    
    def __init__(self):
        """Initialize trading bot"""
        # Get API credentials from environment
        api_key = os.getenv('BINANCE_API_KEY')
        secret_key = os.getenv('BINANCE_SECRET_KEY')
        testnet = os.getenv('BINANCE_TESTNET', 'False').lower() == 'true'
        
        if not api_key or not secret_key:
            raise ValueError("BINANCE_API_KEY and BINANCE_SECRET_KEY must be set in .env file")
        
        # Initialize exchange and position manager
        self.exchange = ExchangeManager(api_key, secret_key, testnet)
        self.position_manager = PositionManager(self.exchange)
        
        # Set leverage
        if not self.exchange.set_leverage(SYMBOL, LEVERAGE):
            logger.warning(f"Failed to set leverage to {LEVERAGE}x")
        
        # Data storage
        self.ohlcv_data: Optional[pd.DataFrame] = None
        self.last_candle_time = None
        
        logger.info("Trading bot initialized")
    
    def calculate_position_size(self, balance: float, risk_pct: float, entry: float, sl: float) -> float:
        """
        Calculate position size based on risk
        
        Args:
            balance: Account balance
            risk_pct: Risk percentage per trade
            entry: Entry price
            sl: Stop loss price
            
        Returns:
            Position size in USDT
        """
        try:
            risk_amt = balance * risk_pct
            dist = abs(entry - sl)
            
            if dist == 0:
                logger.warning("Stop loss equals entry price, using minimum size")
                return MIN_ORDER_SIZE
            
            # Calculate size: risk_amount / distance * entry_price
            raw_size = (risk_amt / dist) * entry
            
            # Ensure minimum order size
            if raw_size < MIN_ORDER_SIZE:
                raw_size = MIN_ORDER_SIZE
                logger.warning(f"Position size too small, adjusted to minimum: {MIN_ORDER_SIZE}")
            
            return raw_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return MIN_ORDER_SIZE
    
    def fetch_and_prepare_data(self) -> bool:
        """
        Fetch and prepare OHLCV data
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch enough candles for all indicators (need at least 89 for EMA89)
            limit = max(CONST_EMA_MACRO, CONST_CHOP_LOOKBACK) + 50
            df = self.exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=limit)
            
            if df is None or len(df) < CONST_EMA_MACRO:
                logger.error(f"Insufficient data: {len(df) if df is not None else 0} candles")
                return False
            
            self.ohlcv_data = df
            return True
            
        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            return False
    
    def on_candle_close(self) -> bool:
        """
        Main execution logic on candle close
        Implements the algorithm from algo.md
        
        Returns:
            True if executed successfully, False otherwise
        """
        try:
            # Fetch latest data
            if not self.fetch_and_prepare_data():
                return False
            
            df = self.ohlcv_data
            if df is None or len(df) < CONST_EMA_MACRO:
                logger.error("Insufficient data for analysis")
                return False
            
            # Get current price (last candle close)
            current_price = float(df['close'].iloc[-1])
            
            # Calculate indicators
            ema7 = calculate_ema(df, CONST_EMA_FAST)
            ema25 = calculate_ema(df, CONST_EMA_SLOW)
            ema89 = calculate_ema(df, CONST_EMA_MACRO)
            atr = calculate_atr(df, CONST_ATR_PERIOD)
            rsi = calculate_rsi(df, CONST_RSI_PERIOD)
            
            # Check if we have enough data
            if len(ema7) < 2 or len(ema25) < 1 or len(ema89) < 1 or len(atr) < 1 or len(rsi) < 1:
                logger.warning("Not enough indicator data")
                return False
            
            # Get latest values
            ema7_current = float(ema7.iloc[-1])
            ema7_prev = float(ema7.iloc[-2]) if len(ema7) >= 2 else ema7_current
            ema25_current = float(ema25.iloc[-1])
            ema89_current = float(ema89.iloc[-1])
            atr_current = float(atr.iloc[-1])
            rsi_current = float(rsi.iloc[-1])
            
            # Calculate deviation and slope
            deviation = calculate_deviation(current_price, ema7_current)
            slope = calculate_slope(ema7_current, ema7_prev)
            
            # Count crosses for chop filter
            cross_count = count_price_ma_crosses(df, CONST_CHOP_LOOKBACK, ema7)
            
            # Get balance
            balance = self.exchange.get_usdt_balance()
            if balance is None or balance <= 0:
                logger.error("Invalid balance")
                return False
            
            # Check daily loss limit
            if self.position_manager.check_daily_loss_limit(MAX_DAILY_LOSS, balance):
                logger.warning("Daily loss limit reached, skipping trading")
                return False
            
            # Sync position from exchange
            self.position_manager.sync_position(SYMBOL)
            
            # --- POSITION MANAGEMENT (PRIORITY 1) ---
            if self.position_manager.has_open_position():
                pos = self.position_manager.get_current_position()
                
                # 1. Flash Take Profit (RSI Logic)
                if pos.side == 'SHORT' and rsi_current < CONST_RSI_OVERSOLD and not pos.partial_tp_taken:
                    logger.info("RSI Oversold flash TP for SHORT position")
                    if self.position_manager.close_position(percentage=50, reason="RSI_OVERSOLD_FLASH_TP"):
                        self.position_manager.mark_partial_tp_taken()
                        # Move SL to breakeven
                        self.position_manager.update_stop_loss(pos.entry_price)
                    return True
                
                if pos.side == 'LONG' and rsi_current > CONST_RSI_OVERBOUGHT and not pos.partial_tp_taken:
                    logger.info("RSI Overbought flash TP for LONG position")
                    if self.position_manager.close_position(percentage=50, reason="RSI_OVERBOUGHT_FLASH_TP"):
                        self.position_manager.mark_partial_tp_taken()
                        # Move SL to breakeven
                        self.position_manager.update_stop_loss(pos.entry_price)
                    return True
                
                # 2. Trend Break Exit
                if pos.side == 'LONG' and current_price < ema25_current:
                    logger.info("Trend broken for LONG position (price < EMA25)")
                    self.position_manager.close_position(percentage=100, reason="TREND_BROKEN_EMA25")
                    return True
                
                if pos.side == 'SHORT' and current_price > ema25_current:
                    logger.info("Trend broken for SHORT position (price > EMA25)")
                    self.position_manager.close_position(percentage=100, reason="TREND_BROKEN_EMA25")
                    return True
                
                # 3. Pyramiding (Aggressive Scale-in)
                distance_moved = abs(current_price - pos.entry_price)
                if (pos.unrealized_pnl > 0 and
                    distance_moved > CONST_PYRAMID_STEP * atr_current and
                    pos.layers < CONST_MAX_LAYERS and
                    deviation < CONST_DEVIATION_MAX):
                    
                    logger.info("Pyramiding condition met, adding layer")
                    # Calculate size for new layer (50% of base)
                    base_size = self.calculate_position_size(balance, CONST_RISK_PER_TRADE, pos.entry_price, pos.stop_loss_price or pos.entry_price)
                    new_size = base_size * 0.5
                    
                    # Convert to contract amount
                    contract_amount = round(new_size / current_price, 3)
                    
                    if contract_amount <= 0:
                        logger.warning(f"Invalid contract amount for pyramiding: {contract_amount}")
                        return True
                    
                    # Execute market order
                    side = 'buy' if pos.side == 'LONG' else 'sell'
                    order = self.exchange.create_market_order(SYMBOL, side, contract_amount)
                    
                    if order:
                        self.position_manager.add_layer(contract_amount)
                        
                        # Trail stop loss
                        if pos.side == 'LONG':
                            new_sl = current_price - 2 * atr_current
                        else:
                            new_sl = current_price + 2 * atr_current
                        
                        self.position_manager.update_stop_loss(new_sl)
                
                return True  # End logic if position exists
            
            # --- ENTRY LOGIC (PRIORITY 2) ---
            
            # 1. Chop Filter
            if cross_count >= CONST_CHOP_MAX_CROSS:
                logger.info(f"Market is choppy (crosses: {cross_count}), skipping entry")
                return True
            
            # 2. Long Entry Conditions
            if (ema25_current > ema89_current and
                current_price > ema7_current and
                slope > CONST_SLOPE_MIN and
                rsi_current < 70 and
                deviation < CONST_DEVIATION_MAX):
                
                logger.info("Long entry conditions met")
                sl_price = current_price - (CONST_HARD_SL_ATR * atr_current)
                size = self.calculate_position_size(balance, CONST_RISK_PER_TRADE, current_price, sl_price)
                
                # Convert size to contract amount (for ETH/USDT, 1 contract = 1 ETH)
                # Size is in USDT, so divide by price to get ETH amount
                contract_amount = size / current_price
                
                # Round to appropriate precision (ETH typically 3 decimal places)
                contract_amount = round(contract_amount, 3)
                
                if contract_amount <= 0:
                    logger.warning(f"Invalid contract amount: {contract_amount}")
                    return True
                
                # Execute market order
                order = self.exchange.create_market_order(SYMBOL, 'buy', contract_amount)
                
                if order:
                    logger.info(f"Long position opened: {contract_amount} ETH @ {current_price}, SL: {sl_price}")
                    # Set stop loss
                    sl_order = self.exchange.create_stop_loss_order(SYMBOL, 'sell', contract_amount, sl_price)
                    if sl_order:
                        self.position_manager.sync_position(SYMBOL)
                        if self.position_manager.current_position:
                            self.position_manager.update_stop_loss(sl_price, sl_order.get('id'))
                    else:
                        logger.warning("Failed to create stop loss order, position opened without SL")
                
                return True
            
            # 3. Short Entry Conditions
            elif (ema25_current < ema89_current and
                  current_price < ema7_current and
                  slope < -CONST_SLOPE_MIN and
                  rsi_current > 30 and
                  deviation < CONST_DEVIATION_MAX):
                
                logger.info("Short entry conditions met")
                sl_price = current_price + (CONST_HARD_SL_ATR * atr_current)
                size = self.calculate_position_size(balance, CONST_RISK_PER_TRADE, current_price, sl_price)
                
                # Convert size to contract amount (for ETH/USDT, 1 contract = 1 ETH)
                # Size is in USDT, so divide by price to get ETH amount
                contract_amount = size / current_price
                
                # Round to appropriate precision (ETH typically 3 decimal places)
                contract_amount = round(contract_amount, 3)
                
                if contract_amount <= 0:
                    logger.warning(f"Invalid contract amount: {contract_amount}")
                    return True
                
                # Execute market order
                order = self.exchange.create_market_order(SYMBOL, 'sell', contract_amount)
                
                if order:
                    logger.info(f"Short position opened: {contract_amount} ETH @ {current_price}, SL: {sl_price}")
                    # Set stop loss
                    sl_order = self.exchange.create_stop_loss_order(SYMBOL, 'buy', contract_amount, sl_price)
                    if sl_order:
                        self.position_manager.sync_position(SYMBOL)
                        if self.position_manager.current_position:
                            self.position_manager.update_stop_loss(sl_price, sl_order.get('id'))
                    else:
                        logger.warning("Failed to create stop loss order, position opened without SL")
                
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Error in on_candle_close: {str(e)}", exc_info=True)
            return False
    
    def run(self):
        """Main run loop"""
        logger.info("Starting trading bot...")
        
        while True:
            try:
                # Check for new candle (every hour for 1h timeframe)
                current_time = datetime.now()
                
                # Run on candle close logic
                self.on_candle_close()
                
                # Wait for next check (check every 5 minutes)
                time.sleep(300)  # 5 minutes
                
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}", exc_info=True)
                time.sleep(60)  # Wait 1 minute before retry


if __name__ == "__main__":
    try:
        bot = TradingBot()
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}", exc_info=True)

