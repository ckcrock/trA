import asyncio
import os
import sys
import logging
import argparse
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Path setup
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger("Backtest")

# Conditional Imports
try:
    from nautilus_trader.backtest.engine import BacktestEngine
    from nautilus_trader.config import BacktestEngineConfig
    from nautilus_trader.model.data import Bar, BarType
    from nautilus_trader.model.identifiers import Venue, InstrumentId, Symbol, TraderId
    from nautilus_trader.model.objects import Money, Currency
    from nautilus_trader.model.enums import OmsType, AccountType
    from nautilus_trader.model.objects import Price, Quantity
    from nautilus_trader.model.instruments import Equity
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False

# Project Imports
from src.adapters.angel.auth import AngelAuthManager
from src.adapters.angel.data_client import AngelDataClient
from src.adapters.angel.rate_limiter import TokenBucketRateLimiter
from src.adapters.nautilus.parsing import parse_bar
from src.strategies.nautilus.ema_cross import EMACross, EMACrossConfig

async def main():
    if not NAUTILUS_AVAILABLE:
        logger.error("Nautilus Trader not installed.")
        return

    # 0. Parse Arguments
    parser = argparse.ArgumentParser(description="Nautilus Backtest with Angel One Data")
    parser.add_argument("--period", type=str, default="1m", choices=["1m", "6m", "1y"], help="Backtest period")
    parser.add_argument("--interval", type=str, default="ONE_DAY", help="Data interval (e.g. ONE_DAY, FIVE_MINUTE)")
    parser.add_argument("--symbol", type=str, default="SBIN", help="Trading symbol")
    parser.add_argument("--token", type=str, default="3045", help="Symbol token")
    args = parser.parse_args()

    load_dotenv()
    
    # 1. Setup Data Client
    api_key = os.getenv("ANGEL_API_KEY")
    auth = AngelAuthManager(
        api_key=api_key,
        client_code=os.getenv("ANGEL_CLIENT_CODE"),
        mpin=os.getenv("ANGEL_PASSWORD"),
        totp_secret=os.getenv("ANGEL_TOTP_SECRET")
    )
    if not auth.login():
        logger.error("Login Failed")
        return
        
    rate_limiter = TokenBucketRateLimiter(3.0)
    data_client = AngelDataClient(auth, rate_limiter)
    
    # 2. Define Instrument
    instrument_id_str = f"{args.symbol}-EQ.NSE"
    instrument = Equity(
        instrument_id=InstrumentId.from_str(instrument_id_str),
        raw_symbol=Symbol(args.symbol),
        currency=Currency.from_str("INR"),
        price_precision=2,
        price_increment=Price.from_str("0.05"),
        lot_size=Quantity.from_str("1"),
        ts_event=0,
        ts_init=0
    )
    logger.info(f"Instrument Defined: {instrument}")

    # 3. Calculate Dates
    to_date = datetime.now()
    if args.period == "1m":
        from_date = to_date - timedelta(days=30)
    elif args.period == "6m":
        from_date = to_date - timedelta(days=180)
    elif args.period == "1y":
        from_date = to_date - timedelta(days=365)
    
    # 4. Fetch Historical Data
    logger.info(f"Fetching {args.period} Historical Data ({args.interval}) for {args.symbol}...")
    df = await data_client.get_historical_data_chunked(
        symbol_token=args.token,
        exchange="NSE",
        interval=args.interval,
        from_date=from_date,
        to_date=to_date
    )
    
    if df is None or df.empty:
        logger.error("❌ No data fetched. Cannot run backtest.")
        return
        
    logger.info(f"Fetched {len(df)} bars.")

    # 5. Convert to Nautilus Bars
    bars = []
    # Interval to string for BarType
    interval_map = {
        "ONE_MINUTE": "1",
        "FIVE_MINUTE": "5",
        "FIFTEEN_MINUTE": "15",
        "ONE_DAY": "1",
    }
    # Handling BarType time unit
    time_unit = "DAY" if args.interval == "ONE_DAY" else "MINUTE"
    bar_type_str = f"{instrument_id_str}-{interval_map.get(args.interval, '1')}-{time_unit}-MID-EXTERNAL"
    bar_type_obj = BarType.from_str(bar_type_str)

    for row in df.itertuples(index=False):
        op = f"{float(row.open):.2f}"
        hi = f"{float(row.high):.2f}"
        lo = f"{float(row.low):.2f}"
        cl = f"{float(row.close):.2f}"
        
        candle = [row.timestamp, op, hi, lo, cl, row.volume]
        bar = parse_bar(bar_type_obj, candle, instrument, 0)
        if bar:
            bars.append(bar)
            
    logger.info(f"Converted {len(bars)} Nautilus bars.")

    # 6. Config Backtest Environment
    engine = BacktestEngine(
        config=BacktestEngineConfig(
            trader_id=TraderId("BACKTESTER-001")
        )
    )
    
    engine.add_venue(
        venue=Venue("NSE"),
        oms_type=OmsType.HEDGING,
        account_type=AccountType.MARGIN,
        starting_balances=[Money(1000000, Currency.from_str("INR"))]
    )
    engine.add_instrument(instrument)
    
    # Add Data
    logger.info("Adding data to engine...")
    engine.add_data(bars)
    
    # 7. Add Strategy
    exec_config = EMACrossConfig(
        instrument_id=instrument_id_str,
        bar_type=bar_type_str,
        fast_period=10,
        slow_period=20,
        quantity=10
    )
    strategy = EMACross(exec_config)
    
    logger.info("Adding strategy...")
    engine.add_strategy(strategy)
    
    # 8. Run
    logger.info("Starting Backtest...")
    engine.run()
    
    logger.info("="*60)
    logger.info("Backtest Complete!")
    logger.info("="*60)
    
    # 9. Report Results & Save
    os.makedirs("backtest_results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"backtest_results/backtest_{args.symbol}_{args.period}_{args.interval}_{timestamp}"

    # Generate Reports
    try:
        account_report = engine.trader.generate_account_report(Venue("NSE"))
        account_report.to_csv(f"{prefix}_account.csv")
        logger.info(f"\n--- Account Report ---\n{account_report}")
    except Exception as e:
        logger.error(f"Failed to generate account report: {e}")

    try:
        fills_report = engine.trader.generate_order_fills_report()
        fills_report.to_csv(f"{prefix}_fills.csv")
    except Exception as e:
        logger.error(f"Failed to generate fills report: {e}")

    try:
        # Try plural first (most common in recent versions)
        positions_report = engine.trader.generate_positions_report()
        positions_report.to_csv(f"{prefix}_positions.csv")
    except AttributeError:
        try:
            # Fallback to singular
            positions_report = engine.trader.generate_position_report()
            positions_report.to_csv(f"{prefix}_positions.csv")
        except Exception as e:
            logger.error(f"Failed to generate positions report: {e}")

    # Statistics
    try:
        stats = engine.trader.generate_statistics_report()
        with open(f"{prefix}_stats.txt", "w") as f:
            f.write(str(stats))
        logger.info(f"\n--- Statistics ---\n{stats}")
    except Exception as e:
        logger.error(f"Failed to generate statistics: {e}")

    logger.info(f"\n✅ Results saved with prefix: {prefix}")

if __name__ == "__main__":
    if NAUTILUS_AVAILABLE:
        asyncio.run(main())
    else:
        print("Nautilus Trader not installed.")
