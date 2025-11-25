"""
Configuration file for TITAN-MA7 QUANT SYSTEM (VERSION 2.1 - RSI ENHANCED)
Contains all constants and configuration parameters
"""

# ================================
# ALGORITHM PARAMETERS
# ================================
CONST_EMA_FAST = 7       # Fast Moving Average
CONST_EMA_SLOW = 25      # Trend Confirmation & Trailing Stop Base
CONST_EMA_MACRO = 89     # Macro Trend Filter (The "River")
CONST_ATR_PERIOD = 14    # Volatility Measure
CONST_RSI_PERIOD = 14    # Momentum Measure

# Risk Settings
CONST_RISK_PER_TRADE = 0.01   # 1% Account Balance per base trade
CONST_MAX_LAYERS = 3          # Max Pyramiding Layers (1 Base + 2 Adds)
CONST_PYRAMID_STEP = 1.5      # Multiplier of ATR to trigger next layer add
CONST_HARD_SL_ATR = 2.0       # Initial Hard Stop Loss distance (ATR multiplier)

# Logic Thresholds
CONST_SLOPE_MIN = 0.04        # Minimum slope percentage to confirm trend
CONST_DEVIATION_MAX = 2.5     # Max allowed distance % from Price to EMA7 (Anti-FOMO)
CONST_CHOP_LOOKBACK = 24      # Bars to look back for sideways detection
CONST_CHOP_MAX_CROSS = 5      # Max Allowed crosses in lookback period
CONST_RSI_OVERBOUGHT = 75     # Flash Exit Trigger Level
CONST_RSI_OVERSOLD = 25       # Flash Exit Trigger Level

# --- CẤU HÌNH CHO TÀI KHOẢN MICRO ($100 - $500) ---
LEVERAGE = 5                   # Giữ nguyên x5 (hoặc x10 nếu muốn ký quỹ ít hơn)
RISK_PER_TRADE = 0.03         # Tăng lên 3% (Chấp nhận mất 3$ để đổi lấy lệnh lớn hơn)
MAX_DAILY_LOSS = 0.10         # Tăng lên 10% (10$) vì vốn nhỏ biến động lớn
MIN_ORDER_SIZE = 10.0         # Set cứng volume tối thiểu là 10$ để tránh lỗi sàn

# ================================
# TRADING SETTINGS
# ================================
SYMBOL = 'ETH/USDT:USDT'      # Perpetual futures symbol
TIMEFRAME = '1h'              # Hourly timeframe
EXCHANGE_ID = 'binanceusdm'   # Binance USD-M Futures

# ================================
# API SETTINGS (Load from environment)
# ================================
# These should be set in .env file:
# BINANCE_API_KEY=your_api_key
# BINANCE_SECRET_KEY=your_secret_key
# BINANCE_TESTNET=False  # Set to True for testnet

