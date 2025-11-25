"""
Technical Indicators Calculation Module
Uses pandas-ta library for reliable indicator calculations
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
from typing import Optional, Tuple


def calculate_ema(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA)
    
    Args:
        df: DataFrame with OHLCV data
        period: Period for EMA calculation
        
    Returns:
        Series with EMA values
    """
    try:
        if df is None or len(df) < period:
            return pd.Series(dtype=float)
        
        ema = ta.ema(df['close'], length=period)
        return ema
    except Exception as e:
        raise ValueError(f"Error calculating EMA({period}): {str(e)}")


def calculate_rsi(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI)
    
    Args:
        df: DataFrame with OHLCV data
        period: Period for RSI calculation
        
    Returns:
        Series with RSI values
    """
    try:
        if df is None or len(df) < period + 1:
            return pd.Series(dtype=float)
        
        rsi = ta.rsi(df['close'], length=period)
        return rsi
    except Exception as e:
        raise ValueError(f"Error calculating RSI({period}): {str(e)}")


def calculate_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Calculate Average True Range (ATR)
    
    Args:
        df: DataFrame with OHLCV data
        period: Period for ATR calculation
        
    Returns:
        Series with ATR values
    """
    try:
        if df is None or len(df) < period + 1:
            return pd.Series(dtype=float)
        
        atr = ta.atr(df['high'], df['low'], df['close'], length=period)
        return atr
    except Exception as e:
        raise ValueError(f"Error calculating ATR({period}): {str(e)}")


def count_price_ma_crosses(df: pd.DataFrame, period: int, ma: pd.Series) -> int:
    """
    Count the number of times price crosses the moving average in the lookback period
    
    Args:
        df: DataFrame with OHLCV data
        period: Lookback period
        ma: Moving average series
        
    Returns:
        Number of crosses in the lookback period
    """
    try:
        if df is None or len(df) < period or ma is None or len(ma) < period:
            return 0
        
        # Get the last 'period' candles
        price = df['close'].tail(period)
        ma_values = ma.tail(period)
        
        if len(price) != len(ma_values):
            return 0
        
        # Calculate crossovers: price crosses above or below MA
        crosses = 0
        for i in range(1, len(price)):
            prev_price = price.iloc[i-1]
            curr_price = price.iloc[i]
            prev_ma = ma_values.iloc[i-1]
            curr_ma = ma_values.iloc[i]
            
            # Check if price crossed MA
            if (prev_price <= prev_ma and curr_price > curr_ma) or \
               (prev_price >= prev_ma and curr_price < curr_ma):
                crosses += 1
        
        return crosses
    except Exception as e:
        raise ValueError(f"Error counting price-MA crosses: {str(e)}")


def calculate_slope(current_value: float, previous_value: float) -> float:
    """
    Calculate percentage slope between two values
    
    Args:
        current_value: Current value
        previous_value: Previous value
        
    Returns:
        Slope percentage
    """
    try:
        if previous_value == 0:
            return 0.0
        return ((current_value - previous_value) / previous_value) * 100
    except Exception as e:
        raise ValueError(f"Error calculating slope: {str(e)}")


def calculate_deviation(price: float, ema: float) -> float:
    """
    Calculate deviation percentage from EMA
    
    Args:
        price: Current price
        ema: EMA value
        
    Returns:
        Deviation percentage
    """
    try:
        if ema == 0:
            return float('inf')
        return abs(price - ema) / ema * 100
    except Exception as e:
        raise ValueError(f"Error calculating deviation: {str(e)}")

