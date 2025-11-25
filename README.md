# TITAN-MA7 QUANT SYSTEM (VERSION 2.1 - RSI ENHANCED)

Trading bot for crypto perpetual futures using the TITAN-MA7 algorithm with RSI enhancement.

## Features

- **Algorithm**: TITAN-MA7 with RSI-enhanced exit signals
- **Asset**: ETH/USDT Perpetual Futures
- **Timeframe**: 1 Hour (1H)
- **Exchange**: Binance USD-M Futures
- **Risk Management**: Configurable risk per trade, daily loss limits, stop loss
- **Pyramiding**: Up to 3 layers with trailing stop loss
- **Technical Indicators**: EMA (7, 25, 89), RSI (14), ATR (14)

## Requirements

- Python 3.8+
- Binance API Key with Futures trading enabled
- Sufficient balance for trading (minimum $10 per order)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd tradingbot-dca-v1-gemin
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file manually with the following content:
```
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
BINANCE_TESTNET=False
```

4. Edit `.env` and add your Binance API credentials:
```
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
BINANCE_TESTNET=False  # Set to True for testnet
```

## Configuration

All algorithm parameters are defined in `config.py`. Key settings:

### Risk Settings (for Micro Accounts $100-$500)
- `LEVERAGE`: 5x
- `RISK_PER_TRADE`: 3% of account balance
- `MAX_DAILY_LOSS`: 10% of account balance
- `MIN_ORDER_SIZE`: $10 minimum order size

### Algorithm Parameters
- `CONST_EMA_FAST`: 7 (Fast Moving Average)
- `CONST_EMA_SLOW`: 25 (Trend Confirmation)
- `CONST_EMA_MACRO`: 89 (Macro Trend Filter)
- `CONST_ATR_PERIOD`: 14 (Volatility Measure)
- `CONST_RSI_PERIOD`: 14 (Momentum Measure)
- `CONST_MAX_LAYERS`: 3 (Max Pyramiding Layers)
- `CONST_RSI_OVERBOUGHT`: 75 (Flash Exit Level)
- `CONST_RSI_OVERSOLD`: 25 (Flash Exit Level)

## Usage

### Running the Bot

```bash
python main.py
```

The bot will:
1. Connect to Binance Futures
2. Set leverage to configured value
3. Monitor the market every 5 minutes
4. Execute trades based on algorithm signals
5. Log all activities to `trading_bot.log`

### Algorithm Logic

#### Entry Conditions (LONG)
- EMA25 > EMA89 (Macro trend up)
- Price > EMA7
- Slope > 0.04% (Strong momentum)
- RSI < 70 (Not overbought)
- Deviation < 2.5% (Not overextended)
- Chop filter passed (Not sideways market)

#### Entry Conditions (SHORT)
- EMA25 < EMA89 (Macro trend down)
- Price < EMA7
- Slope < -0.04% (Strong downward momentum)
- RSI > 30 (Not oversold)
- Deviation < 2.5% (Not overextended)
- Chop filter passed (Not sideways market)

#### Exit Conditions
1. **Flash TP**: RSI reaches overbought (75) for LONG or oversold (25) for SHORT - closes 50% and moves SL to breakeven
2. **Trend Break**: Price closes on wrong side of EMA25 - closes 100%
3. **Stop Loss**: Hard stop loss at 2.0 ATR from entry

#### Pyramiding
- Adds 50% of base size when:
  - Unrealized PnL > 0
  - Price moved > 1.5 ATR from entry
  - Layers < 3
  - Deviation < 2.5%
- Trails stop loss to 2 ATR from current price

## File Structure

```
.
├── main.py                 # Main bot logic
├── config.py               # Configuration and constants
├── exchange.py             # Exchange interface (CCXT)
├── position_manager.py     # Position tracking and management
├── indicators.py           # Technical indicator calculations
├── algo.md                 # Algorithm documentation
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── README.md              # This file
```

## Important Notes

⚠️ **WARNING**: This bot trades with real money. Always:
- Test on testnet first (`BINANCE_TESTNET=True`)
- Start with small amounts
- Monitor the bot closely
- Understand the risks involved
- Never share your API keys

### API Key Permissions

Your Binance API key needs:
- ✅ Enable Reading
- ✅ Enable Futures Trading
- ❌ Enable Withdrawals (NOT recommended for security)

### Safety Features

- Daily loss limit protection
- Minimum order size enforcement
- Comprehensive error handling
- Position size calculation based on risk
- Stop loss orders for all positions

## Troubleshooting

### Common Issues

1. **"Insufficient balance"**: Ensure you have enough USDT in your futures account
2. **"API key error"**: Check your API key permissions and ensure Futures trading is enabled
3. **"Network error"**: Check your internet connection and Binance API status
4. **"Order size too small"**: Minimum order size is $10, adjust `MIN_ORDER_SIZE` in config if needed

### Logs

Check `trading_bot.log` for detailed execution logs and error messages.

## License

This project is for educational purposes. Use at your own risk.

## Disclaimer

Trading cryptocurrencies involves substantial risk of loss. This bot is provided as-is without any warranty. The authors are not responsible for any financial losses incurred from using this software.

