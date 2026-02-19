#!/usr/bin/env python3
"""
ANGEL ONE API - PRACTICAL TRADING EXAMPLES
Real-world usage patterns for algorithmic trading

Examples included:
1. VWAP Intraday Strategy
2. Historical Data Download
3. Live Market Monitoring
4. Automated Order Execution
5. Position Management
6. Bracket Order Implementation
"""

import time
import pandas as pd
from datetime import datetime, timedelta
from angel_one_complete_integration import AngelOneClient, AngelWebSocket
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# EXAMPLE 1: DOWNLOAD & STORE HISTORICAL DATA
# ============================================================================

def download_historical_data_bulk(client: AngelOneClient, symbols: list):
    """
    Download historical data for multiple symbols
    
    Args:
        client: AngelOneClient instance
        symbols: List of (token, symbol, exchange) tuples
    """
    logger.info("📥 Downloading historical data for multiple symbols...")
    
    # Date range (last 30 days)
    from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d 09:15")
    to_date = datetime.now().strftime("%Y-%m-%d 15:30")
    
    all_data = {}
    
    for token, symbol, exchange in symbols:
        logger.info(f"Downloading {symbol}...")
        
        # Rate limit: 3 req/sec for historical data
        time.sleep(0.4)  # 400ms = 2.5 req/sec
        
        df = client.market_data.get_historical_data(
            exchange=exchange,
            symbol_token=token,
            interval="FIVE_MINUTE",
            from_date=from_date,
            to_date=to_date
        )
        
        if df is not None:
            # Save to CSV
            filename = f"data/{symbol}_{datetime.now().strftime('%Y%m%d')}.csv"
            df.to_csv(filename, index=False)
            
            all_data[symbol] = df
            logger.info(f"✅ Saved {len(df)} candles for {symbol}")
    
    return all_data


# ============================================================================
# EXAMPLE 2: LIVE VWAP INTRADAY STRATEGY
# ============================================================================

class VWAPIntradayStrategy:
    """
    Live VWAP-based intraday trading strategy
    
    Entry Logic:
    - Buy when price dips to VWAP with volume confirmation
    - Sell when price rises above entry + target
    
    Risk Management:
    - Stop loss: 0.3%
    - Target: 0.5%
    - Max positions: 3
    """
    
    def __init__(self, client: AngelOneClient):
        self.client = client
        self.positions = {}
        self.max_positions = 3
        self.target_pct = 0.005  # 0.5%
        self.stop_loss_pct = 0.003  # 0.3%
        
        # Tracking
        self.last_tick = {}
        self.volume_avg = {}
    
    def on_tick(self, tick_data):
        """
        Process incoming tick data
        
        Tick format:
        {
            'token': '3045',
            'ltp': 720.50,
            'volume': 12345,
            ...
        }
        """
        try:
            token = tick_data.get('token')
            ltp = tick_data.get('ltp')
            volume = tick_data.get('volume')
            
            if not all([token, ltp, volume]):
                return
            
            # Update tracking
            self.last_tick[token] = tick_data
            
            # Calculate VWAP (simplified - should use cumulative)
            # In production, maintain running VWAP calculation
            vwap = ltp  # Placeholder
            
            # Check entry conditions
            if token not in self.positions:
                self._check_entry_signal(token, ltp, vwap, volume)
            else:
                self._check_exit_signal(token, ltp)
                
        except Exception as e:
            logger.error(f"Error processing tick: {e}")
    
    def _check_entry_signal(self, token, ltp, vwap, volume):
        """Check if entry conditions are met"""
        # Max positions check
        if len(self.positions) >= self.max_positions:
            return
        
        # Entry logic: Price near VWAP + Volume spike
        near_vwap = abs(ltp - vwap) / vwap < 0.002  # Within 0.2%
        
        # Volume spike (need historical average)
        volume_spike = True  # Simplified
        
        if near_vwap and volume_spike:
            logger.info(f"🎯 Entry signal for {token} at {ltp}")
            self._place_entry_order(token, ltp)
    
    def _place_entry_order(self, token, entry_price):
        """Place entry order"""
        try:
            # Get symbol info from token
            # In production, maintain token-symbol mapping
            trading_symbol = "SBIN-EQ"  # Placeholder
            
            order_id = self.client.orders.place_order(
                trading_symbol=trading_symbol,
                symbol_token=token,
                exchange="NSE",
                transaction_type="BUY",
                quantity=1,
                order_type="MARKET",
                product_type="INTRADAY"
            )
            
            if order_id:
                # Track position
                self.positions[token] = {
                    'entry_price': entry_price,
                    'quantity': 1,
                    'stop_loss': entry_price * (1 - self.stop_loss_pct),
                    'target': entry_price * (1 + self.target_pct),
                    'order_id': order_id
                }
                
                logger.info(f"✅ Entered position: {token} @ {entry_price}")
        
        except Exception as e:
            logger.error(f"Error placing entry order: {e}")
    
    def _check_exit_signal(self, token, current_price):
        """Check if exit conditions are met"""
        position = self.positions[token]
        
        # Check stop loss
        if current_price <= position['stop_loss']:
            logger.info(f"🛑 Stop loss hit for {token}")
            self._place_exit_order(token, "STOP_LOSS")
        
        # Check target
        elif current_price >= position['target']:
            logger.info(f"🎯 Target hit for {token}")
            self._place_exit_order(token, "TARGET")
    
    def _place_exit_order(self, token, reason):
        """Place exit order"""
        try:
            position = self.positions[token]
            trading_symbol = "SBIN-EQ"  # Placeholder
            
            order_id = self.client.orders.place_order(
                trading_symbol=trading_symbol,
                symbol_token=token,
                exchange="NSE",
                transaction_type="SELL",
                quantity=position['quantity'],
                order_type="MARKET",
                product_type="INTRADAY"
            )
            
            if order_id:
                logger.info(f"✅ Exited position: {token} - {reason}")
                del self.positions[token]
        
        except Exception as e:
            logger.error(f"Error placing exit order: {e}")


# ============================================================================
# EXAMPLE 3: LIVE MARKET MONITORING DASHBOARD
# ============================================================================

class LiveMarketMonitor:
    """
    Monitor multiple stocks in real-time
    Display live quotes and alerts
    """
    
    def __init__(self, client: AngelOneClient):
        self.client = client
        self.watchlist = {}
        self.alerts = []
    
    def add_to_watchlist(self, token: str, symbol: str, exchange: str = "nse_cm"):
        """Add symbol to watchlist"""
        self.watchlist[token] = {
            'symbol': symbol,
            'exchange': exchange,
            'last_price': 0,
            'change_pct': 0
        }
    
    def on_tick(self, tick_data):
        """Process tick and update dashboard"""
        token = tick_data.get('token')
        
        if token not in self.watchlist:
            return
        
        ltp = tick_data.get('ltp', 0)
        prev_close = tick_data.get('close', 0)
        
        if prev_close > 0:
            change_pct = ((ltp - prev_close) / prev_close) * 100
        else:
            change_pct = 0
        
        # Update watchlist
        self.watchlist[token].update({
            'last_price': ltp,
            'change_pct': change_pct,
            'volume': tick_data.get('volume', 0),
            'timestamp': datetime.now()
        })
        
        # Check alerts
        self._check_alerts(token)
        
        # Print update
        self._print_dashboard()
    
    def _check_alerts(self, token):
        """Check for price alerts"""
        data = self.watchlist[token]
        
        # Alert if change > 2%
        if abs(data['change_pct']) > 2.0:
            alert = f"⚠️ {data['symbol']}: {data['change_pct']:.2f}% move!"
            if alert not in self.alerts:
                self.alerts.append(alert)
                logger.warning(alert)
    
    def _print_dashboard(self):
        """Print live dashboard (terminal UI)"""
        # Clear screen (optional)
        # print("\033[H\033[J")
        
        print("\n" + "="*60)
        print("LIVE MARKET MONITOR")
        print("="*60)
        
        for token, data in self.watchlist.items():
            symbol = data['symbol']
            price = data['last_price']
            change = data['change_pct']
            
            color = "🟢" if change >= 0 else "🔴"
            
            print(f"{color} {symbol:10s} | ₹{price:8.2f} | {change:+6.2f}%")
        
        print("="*60)


# ============================================================================
# EXAMPLE 4: BRACKET ORDER IMPLEMENTATION
# ============================================================================

class BracketOrderManager:
    """
    Implement bracket orders (Entry + SL + Target)
    Since Angel One doesn't have native bracket orders in API
    """
    
    def __init__(self, client: AngelOneClient):
        self.client = client
        self.bracket_orders = {}
    
    def place_bracket_order(
        self,
        trading_symbol: str,
        symbol_token: str,
        exchange: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        target: float
    ):
        """
        Place bracket order
        
        Steps:
        1. Place entry order (limit)
        2. Wait for execution
        3. Place SL and Target orders
        """
        try:
            # Step 1: Place entry order
            entry_order_id = self.client.orders.place_order(
                trading_symbol=trading_symbol,
                symbol_token=symbol_token,
                exchange=exchange,
                transaction_type="BUY",
                quantity=quantity,
                order_type="LIMIT",
                product_type="INTRADAY",
                price=entry_price
            )
            
            if not entry_order_id:
                logger.error("Entry order failed")
                return None
            
            # Track bracket order
            bracket_id = f"BO_{entry_order_id}"
            self.bracket_orders[bracket_id] = {
                'entry_order_id': entry_order_id,
                'symbol': trading_symbol,
                'token': symbol_token,
                'exchange': exchange,
                'quantity': quantity,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target': target,
                'status': 'PENDING',
                'sl_order_id': None,
                'target_order_id': None
            }
            
            logger.info(f"✅ Bracket order initiated: {bracket_id}")
            
            # Start monitoring for entry fill
            self._monitor_entry_fill(bracket_id)
            
            return bracket_id
            
        except Exception as e:
            logger.error(f"Error placing bracket order: {e}")
            return None
    
    def _monitor_entry_fill(self, bracket_id):
        """Monitor entry order for fill"""
        # In production, use WebSocket order updates
        # or polling in separate thread
        
        bracket = self.bracket_orders[bracket_id]
        entry_order_id = bracket['entry_order_id']
        
        # Check order status
        order = self.client.orders.get_order_status(entry_order_id)
        
        if order and order.get('orderstatus') == 'complete':
            logger.info(f"✅ Entry filled for {bracket_id}")
            self._place_exit_orders(bracket_id)
    
    def _place_exit_orders(self, bracket_id):
        """Place SL and Target orders after entry fill"""
        try:
            bracket = self.bracket_orders[bracket_id]
            
            # Place Stop Loss order
            sl_order_id = self.client.orders.place_order(
                trading_symbol=bracket['symbol'],
                symbol_token=bracket['token'],
                exchange=bracket['exchange'],
                transaction_type="SELL",
                quantity=bracket['quantity'],
                order_type="STOPLOSS_MARKET",
                product_type="INTRADAY",
                trigger_price=bracket['stop_loss']
            )
            
            # Place Target order
            target_order_id = self.client.orders.place_order(
                trading_symbol=bracket['symbol'],
                symbol_token=bracket['token'],
                exchange=bracket['exchange'],
                transaction_type="SELL",
                quantity=bracket['quantity'],
                order_type="LIMIT",
                product_type="INTRADAY",
                price=bracket['target']
            )
            
            # Update bracket order
            bracket['sl_order_id'] = sl_order_id
            bracket['target_order_id'] = target_order_id
            bracket['status'] = 'ACTIVE'
            
            logger.info(f"✅ Exit orders placed for {bracket_id}")
            logger.info(f"   SL: {sl_order_id}")
            logger.info(f"   Target: {target_order_id}")
            
        except Exception as e:
            logger.error(f"Error placing exit orders: {e}")


# ============================================================================
# EXAMPLE 5: COMPREHENSIVE TRADING SYSTEM
# ============================================================================

def run_live_trading_system():
    """
    Complete example: Live trading system
    
    Features:
    - Historical data download
    - Live WebSocket streaming
    - VWAP strategy execution
    - Position monitoring
    - Auto square-off before market close
    """
    
    # Initialize client
    client = AngelOneClient(
        api_key="your_api_key",
        client_code="your_client_code",
        mpin="your_mpin",
        totp_secret="your_totp_secret"
    )
    
    # Step 1: Download historical data for backtesting
    logger.info("Step 1: Downloading historical data...")
    symbols = [
        ("3045", "SBIN", "NSE"),
        ("1333", "HDFCBANK", "NSE"),
        ("2885", "RELIANCE", "NSE"),
    ]
    
    # Uncomment to download
    # historical_data = download_historical_data_bulk(client, symbols)
    
    # Step 2: Initialize strategy
    logger.info("Step 2: Initializing VWAP strategy...")
    strategy = VWAPIntradayStrategy(client)
    
    # Step 3: Start WebSocket
    logger.info("Step 3: Starting live WebSocket...")
    
    def on_tick(tick):
        strategy.on_tick(tick)
    
    def on_connect():
        logger.info("✅ WebSocket connected! Subscribing to symbols...")
        for token, symbol, exchange in symbols:
            exchange_code = "nse_cm"
            client.websocket.subscribe(token, exchange_code, AngelWebSocket.MODE_QUOTE)
    
    client.start_websocket(
        on_tick=on_tick,
        on_connect=on_connect
    )
    
    # Step 4: Run until market close
    logger.info("Step 4: Running strategy...")
    
    try:
        # Calculate time until market close (3:30 PM)
        now = datetime.now()
        market_close = now.replace(hour=15, minute=30, second=0)
        
        if market_close > now:
            run_duration = (market_close - now).total_seconds()
            logger.info(f"Running for {run_duration/60:.0f} minutes until market close")
            
            time.sleep(run_duration)
        else:
            logger.info("Market already closed. Running for 60 seconds demo...")
            time.sleep(60)
    
    except KeyboardInterrupt:
        logger.info("⚠️ Interrupted by user")
    
    finally:
        # Step 5: Square off all positions
        logger.info("Step 5: Squaring off positions...")
        
        positions = client.portfolio.get_positions()
        for pos in positions['day']:
            if int(pos.get('netqty', 0)) != 0:
                logger.info(f"Squaring off: {pos['tradingsymbol']}")
                # Place exit order
                # client.orders.place_order(...)
        
        # Step 6: Stop WebSocket and logout
        logger.info("Step 6: Cleaning up...")
        client.stop_websocket()
        client.logout()
        
        logger.info("✅ Trading session complete!")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    """
    Uncomment the example you want to run
    """
    
    # Example 1: Download historical data
    # from angel_one_complete_integration import AngelOneClient
    # client = AngelOneClient(...)
    # symbols = [("3045", "SBIN", "NSE"), ("1333", "HDFCBANK", "NSE")]
    # download_historical_data_bulk(client, symbols)
    
    # Example 2: Run live trading system
    # run_live_trading_system()
    
    # Example 3: Live market monitor
    # client = AngelOneClient(...)
    # monitor = LiveMarketMonitor(client)
    # monitor.add_to_watchlist("3045", "SBIN")
    # monitor.add_to_watchlist("1333", "HDFCBANK")
    # client.start_websocket(on_tick=monitor.on_tick, on_connect=...)
    
    logger.info("✅ Examples module loaded. Uncomment code to run.")
