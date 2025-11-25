```python
"""
ALGORITHM NAME: TITAN-MA7 QUANT SYSTEM (VERSION 2.1 - RSI ENHANCED)
ASSET CLASS: CRYPTO PERPETUAL FUTURES (ETH/USDT)
TIMEFRAME: 1H (Hourly)
"""

# ================================
# 1. PARAMETERS DEFINITION
# ================================
CONST_EMA_FAST      = 7       # Fast Moving Average
CONST_EMA_SLOW      = 25      # Trend Confirmation & Trailing Stop Base
CONST_EMA_MACRO     = 89      # Macro Trend Filter (The "River")
CONST_ATR_PERIOD    = 14      # Volatility Measure
CONST_RSI_PERIOD    = 14      # Momentum Measure

# Risk Settings
CONST_RISK_PER_TRADE = 0.01   # 1% Account Balance per base trade
CONST_MAX_LAYERS     = 3      # Max Pyramiding Layers (1 Base + 2 Adds)
CONST_PYRAMID_STEP   = 1.5    # Multiplier of ATR to trigger next layer add
CONST_HARD_SL_ATR    = 2.0    # Initial Hard Stop Loss distance (ATR multiplier)

# Logic Thresholds
CONST_SLOPE_MIN      = 0.04   # Minimum slope percentage to confirm trend
CONST_DEVIATION_MAX  = 2.5    # Max allowed distance % from Price to EMA7 (Anti-FOMO)
CONST_CHOP_LOOKBACK  = 24     # Bars to look back for sideways detection
CONST_CHOP_MAX_CROSS = 5      # Max Allowed crosses in lookback period
CONST_RSI_OVERBOUGHT = 75     # Flash Exit Trigger Level
CONST_RSI_OVERSOLD   = 25     # Flash Exit Trigger Level

# --- CẤU HÌNH CHO TÀI KHOẢN MICRO ($100 - $500) ---

LEVERAGE            = 5       # Giữ nguyên x5 (hoặc x10 nếu muốn ký quỹ ít hơn)
RISK_PER_TRADE      = 0.03    # Tăng lên 3% (Chấp nhận mất 3$ để đổi lấy lệnh lớn hơn)
MAX_DAILY_LOSS      = 0.10    # Tăng lên 10% (10$) vì vốn nhỏ biến động lớn
MIN_ORDER_SIZE      = 10.0    # Set cứng volume tối thiểu là 10$ để tránh lỗi sàn

# Logic điều chỉnh Size nếu tính ra quá nhỏ
def calculate_position_size(balance, risk_pct, entry, sl):
    risk_amt = balance * risk_pct
    dist = abs(entry - sl)
    raw_size = (risk_amt / dist) * entry
    
    # Nếu size tính ra nhỏ hơn 10$, ép nó lên 10$ (chấp nhận rủi ro tăng nhẹ)
    # hoặc bỏ lệnh. Ở đây ta chọn ép lên để bot hoạt động.
    if raw_size < MIN_ORDER_SIZE:
        raw_size = MIN_ORDER_SIZE 
        
    return raw_size


# ================================
# 2. MAIN EXECUTION LOOP (ON CANDLE CLOSE)
# ================================
def on_candle_close(balance, positions, candle_data):
    
    # --- A. DATA PREPARATION ---
    current_price = candle_data['close']
    ema7  = calculate_ema(CONST_EMA_FAST)
    ema25 = calculate_ema(CONST_EMA_SLOW)
    ema89 = calculate_ema(CONST_EMA_MACRO)
    atr   = calculate_atr(CONST_ATR_PERIOD)
    rsi   = calculate_rsi(CONST_RSI_PERIOD)
    
    # Calculate Deviation %: abs(Price - EMA7) / EMA7 * 100
    deviation = abs(current_price - ema7) / ema7 * 100
    
    # Calculate Slope %: (EMA7_now - EMA7_prev) / EMA7_prev * 100
    slope = (ema7 - ema7_prev) / ema7_prev * 100

    # Count Crosses for Chop Filter
    cross_count = count_price_ma_crosses(period=CONST_CHOP_LOOKBACK, ma=ema7)

    # --- B. POSITION MANAGEMENT (PRIORITY 1) ---
    if has_open_position():
        pos = get_current_position()
        
        # 1. Flash Take Profit (RSI Logic - Critical for V-Shape Reversal)
        if (pos.side == 'SHORT' and rsi < CONST_RSI_OVERSOLD and not pos.partial_tp_taken):
            close_position(percentage=50, reason="RSI_OVERSOLD_FLASH_TP")
            set_flag(partial_tp_taken=True)
            move_stop_loss(price=pos.entry_price) # Move SL to Breakeven
            return

        if (pos.side == 'LONG' and rsi > CONST_RSI_OVERBOUGHT and not pos.partial_tp_taken):
            close_position(percentage=50, reason="RSI_OVERBOUGHT_FLASH_TP")
            set_flag(partial_tp_taken=True)
            move_stop_loss(price=pos.entry_price)
            return

        # 2. Trend Break Exit (Defensive Exit)
        # If Price closes on the wrong side of EMA25 -> GET OUT IMMEDIATELY
        if (pos.side == 'LONG' and current_price < ema25):
            close_position(percentage=100, reason="TREND_BROKEN_EMA25")
            return
        if (pos.side == 'SHORT' and current_price > ema25):
            close_position(percentage=100, reason="TREND_BROKEN_EMA25")
            return

        # 3. Pyramiding (Aggressive Scale-in)
        # Only add if: PnL > 0 AND Price moved favorable distance AND Not FOMO-ing
        distance_moved = abs(current_price - pos.entry_price)
        if (pos.unrealized_pnl > 0) and \
           (distance_moved > CONST_PYRAMID_STEP * atr) and \
           (pos.layers < CONST_MAX_LAYERS) and \
           (deviation < CONST_DEVIATION_MAX):
            
            # Add 50% of Base Size
            new_size = calculate_position_size(balance, CONST_RISK_PER_TRADE) * 0.5
            execute_market_order(side=pos.side, size=new_size)
            
            # Trail Stop Loss tightly
            new_sl = (current_price - 2*atr) if pos.side == 'LONG' else (current_price + 2*atr)
            update_stop_loss(price=new_sl)
        
        return # End logic if position exists

    # --- C. ENTRY LOGIC (PRIORITY 2) ---
    
    # 1. Chop Filter (Sideway Protection)
    if cross_count >= CONST_CHOP_MAX_CROSS:
        log("Market is Choppy/Sideways. Skipping.")
        return

    # 2. Long Entry Conditions (ALL MUST BE TRUE)
    # - Macro Trend Up (EMA25 > EMA89)
    # - Price above Fast MA
    # - Momentum Strong (Slope > 0.04%)
    # - Not Overbought (RSI < 70)
    # - Not Overextended (Deviation < 2.5%)
    if (ema25 > ema89) and \
       (current_price > ema7) and \
       (slope > CONST_SLOPE_MIN) and \
       (rsi < 70) and \
       (deviation < CONST_DEVIATION_MAX):
        
        sl_price = current_price - (CONST_HARD_SL_ATR * atr)
        size = calculate_position_size(balance, CONST_RISK_PER_TRADE, entry=current_price, sl=sl_price)
        execute_market_order(side='LONG', size=size, stop_loss=sl_price)

    # 3. Short Entry Conditions
    # - Macro Trend Down (EMA25 < EMA89)
    # - Price below Fast MA
    # - Momentum Strong Down (Slope < -0.04%)
    # - Not Oversold (RSI > 30)
    # - Not Overextended (Deviation < 2.5%)
    elif (ema25 < ema89) and \
         (current_price < ema7) and \
         (slope < -CONST_SLOPE_MIN) and \
         (rsi > 30) and \
         (deviation < CONST_DEVIATION_MAX):
        
        sl_price = current_price + (CONST_HARD_SL_ATR * atr)
        size = calculate_position_size(balance, CONST_RISK_PER_TRADE, entry=current_price, sl=sl_price)
        execute_market_order(side='SHORT', size=size, stop_loss=sl_price)

# ================================
# END OF ALGORITHM
# ================================
```

