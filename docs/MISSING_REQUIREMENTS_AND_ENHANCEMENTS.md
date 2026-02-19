# MISSING REQUIREMENTS & CRITICAL ENHANCEMENTS
## Indian Stock Market Trading System - Expert Fintech Analysis

**Date:** February 2026  
**Market:** NSE/BSE - Indian Stock Markets  
**Regulatory Framework:** SEBI 2025 Guidelines  

---

## EXECUTIVE SUMMARY

After comprehensive research on Indian stock market mechanics, SEBI regulations, and trading strategies, this document outlines **22 critical missing requirements** that must be added to your algorithmic trading system for production readiness in the Indian market context.

---

## PART 1: REGULATORY & COMPLIANCE REQUIREMENTS

### 1.1 SEBI Algo Trading Compliance (CRITICAL - NEW 2025 REGULATIONS)

**Status:** 🔴 **MISSING - MANDATORY**

SEBI introduced comprehensive algo trading regulations in 2025 requiring all algorithms to be approved by exchanges, tagged with unique identifiers, and meet strict technical standards.

**Required Implementations:**

```python
# src/compliance/sebi_compliance.py
class SEBIAlgoComplianceManager:
    """
    Manages SEBI algorithmic trading compliance requirements.
    Reference: SEBI/HO/MIRSD/MIRSD-PoD1/P/CIR/2024/169
    """
    
    def __init__(self):
        self.algo_id = None  # Exchange-assigned unique algo ID
        self.registration_status = "UNREGISTERED"
        self.static_ips = []  # Whitelisted static IPs
        self.order_count_per_second = 0
        self.ops_threshold = 10  # Orders Per Second threshold
        
    async def register_algorithm_with_exchange(
        self,
        strategy_name: str,
        strategy_logic: dict,
        algo_type: str,  # "WHITE_BOX" or "BLACK_BOX"
    ):
        """
        Register algorithm with NSE/BSE before deployment.
        MANDATORY: No algo can go live without exchange approval.
        """
        registration_data = {
            "strategy_name": strategy_name,
            "strategy_type": algo_type,
            "logic_description": strategy_logic,
            "risk_parameters": self._extract_risk_params(),
            "broker_code": settings.BROKER_CODE,
        }
        
        # Submit to exchange API for approval
        response = await self._submit_to_exchange(registration_data)
        
        if response["status"] == "APPROVED":
            self.algo_id = response["algo_id"]
            self.registration_status = "REGISTERED"
            logger.info(f"Algorithm registered with ID: {self.algo_id}")
        else:
            raise ComplianceError(f"Algorithm registration failed: {response['reason']}")
    
    def tag_order_with_algo_id(self, order_params: dict) -> dict:
        """
        MANDATORY: Tag every algo order with exchange-assigned algo ID.
        Orders without algo_id will be rejected by broker.
        """
        if self.registration_status != "REGISTERED":
            raise ComplianceError("Algorithm not registered with exchange")
        
        if self.order_count_per_second > self.ops_threshold:
            raise ComplianceError(
                f"OPS threshold exceeded: {self.order_count_per_second} > {self.ops_threshold}"
            )
        
        order_params["algo_id"] = self.algo_id
        order_params["algo_tag"] = "ALGO"
        
        self.order_count_per_second += 1
        return order_params
    
    async def validate_static_ip(self, request_ip: str) -> bool:
        """
        Validate that API requests come from whitelisted static IPs.
        MANDATORY: Only whitelisted IPs can place algo orders.
        """
        if request_ip not in self.static_ips:
            logger.error(f"Order rejected: IP {request_ip} not whitelisted")
            return False
        return True
    
    def enable_two_factor_authentication(self):
        """
        Implement 2FA for all API sessions.
        MANDATORY: OAuth, password expiry, 2FA validation.
        """
        pass
    
    def daily_session_logout(self):
        """
        MANDATORY: All API sessions must logout at end of trading day.
        """
        pass
    
    def maintain_audit_trail(self, order_data: dict):
        """
        Maintain detailed 5-year audit trail for all algo orders.
        MANDATORY: Complete traceability of all algorithm actions.
        """
        audit_record = {
            "timestamp": datetime.now(),
            "algo_id": self.algo_id,
            "order_details": order_data,
            "user_id": order_data.get("user_id"),
            "source_ip": order_data.get("source_ip"),
        }
        # Store in database with 5-year retention
        await self.audit_db.insert(audit_record)
```

**Compliance Checklist:**

- [ ] **Static IP Registration:** Register 1-2 static IPs with broker
- [ ] **Algorithm Registration:** Get exchange approval before deployment
- [ ] **Algo ID Tagging:** Tag every algo order with exchange-assigned ID
- [ ] **OPS Monitoring:** Enforce 10 orders/second threshold (register if exceeding)
- [ ] **2FA Implementation:** OAuth-based 2FA for all API access
- [ ] **Daily Logout:** Auto-logout all sessions before next trading day
- [ ] **Audit Trail:** Maintain 5-year detailed logs
- [ ] **Server Location:** Host algos on Indian servers (SEBI requirement)

**Penalty for Non-Compliance:** Algorithm rejection, broker penalties, potential SEBI action

---

### 1.2 Settlement Cycle Handling (T+1 / T+0)

**Status:** 🟡 **PARTIALLY IMPLEMENTED**

India shifted from T+2 to T+1 settlement in January 2023, with optional T+0 settlement launched in beta for 500 stocks in January 2025.

**Required Implementations:**

```python
# src/settlement/settlement_manager.py
class SettlementManager:
    """
    Manages T+1 and optional T+0 settlement cycles.
    """
    
    def __init__(self):
        self.settlement_type = "T+1"  # Default
        self.t0_eligible_stocks = self._load_t0_stocks()
    
    def calculate_settlement_date(self, trade_date: datetime, symbol: str) -> datetime:
        """
        Calculate settlement date based on T+1 or T+0.
        
        T+1: Settlement happens 1 trading day after execution
        T+0: Optional same-day settlement (select stocks only)
        """
        if symbol in self.t0_eligible_stocks and self.settlement_type == "T+0":
            # T+0: Trades until 1:30 PM settle same day by 3:30 PM
            if trade_date.hour <= 13 and trade_date.minute <= 30:
                return trade_date  # Same day settlement
        
        # T+1: Standard settlement
        return self._next_trading_day(trade_date)
    
    def handle_pay_in_pay_out(self, trade: dict):
        """
        Handle pay-in and pay-out timelines.
        
        T+1 Timeline:
        - T day: Trade execution
        - T day 9:00 PM: Provisional obligations
        - T+1 day 9:00 AM: Final obligations
        - T+1 day 11:00 AM: Pay-in deadline
        - T+1 day 3:30 PM: Pay-out to clients
        """
        settlement_date = self.calculate_settlement_date(
            trade["trade_date"], 
            trade["symbol"]
        )
        
        pay_in_deadline = settlement_date.replace(hour=11, minute=0)
        pay_out_time = settlement_date.replace(hour=15, minute=30)
        
        return {
            "settlement_date": settlement_date,
            "pay_in_deadline": pay_in_deadline,
            "pay_out_time": pay_out_time,
        }
    
    def handle_short_delivery_auction(self, short_delivery: dict):
        """
        Handle buy-in auction for short deliveries.
        
        If seller fails to deliver shares:
        - T+1 day: Buy-in auction conducted
        - T+2 day: Auction settlement
        """
        pass
```

**Key Considerations:**
- Direct payout to client demat accounts mandated by SEBI as of June 2024
- Handle auction penalties for short deliveries
- Track settlement obligations (delivery/receipt positions)

---

### 1.3 Circuit Breaker & Price Band Handling

**Status:** 🔴 **MISSING - CRITICAL**

NSE/BSE implement market-wide circuit breakers at 10%, 15%, and 20% levels, plus individual stock price bands ranging from 2% to 20%.

**Required Implementations:**

```python
# src/risk/circuit_breaker_manager.py
class CircuitBreakerManager:
    """
    Handles market-wide and stock-specific circuit breakers.
    """
    
    # Market-Wide Circuit Breakers (Index-level)
    MWCB_LEVELS = {
        "LEVEL_1": 0.10,  # 10% decline
        "LEVEL_2": 0.15,  # 15% decline
        "LEVEL_3": 0.20,  # 20% decline
    }
    
    # Stock-specific price bands
    PRICE_BANDS = {
        "2_PERCENT": 0.02,   # High volatility/surveillance stocks
        "5_PERCENT": 0.05,   # Moderate liquidity stocks
        "10_PERCENT": 0.10,  # Standard stocks
        "20_PERCENT": 0.20,  # Liquid, well-traded stocks
        "NO_LIMIT": None,    # F&O stocks (derivatives eligible)
    }
    
    def __init__(self):
        self.mwcb_status = "NORMAL"
        self.circuit_limits = self._load_daily_circuit_limits()
        self.halted_stocks = set()
    
    def check_market_wide_circuit_breaker(
        self, 
        index_name: str,  # "NIFTY_50" or "SENSEX"
        current_level: float,
        previous_close: float
    ) -> dict:
        """
        Check if index movement triggers market-wide halt.
        
        MWCB Halt Durations:
        - 10% before 1:00 PM: 45-minute halt
        - 10% between 1:00-2:30 PM: 15-minute halt
        - 10% after 2:30 PM: Market close for day
        - 15%: Similar timings, longer halts
        - 20%: Market closed for day (any time)
        """
        decline = (current_level - previous_close) / previous_close
        
        if abs(decline) >= self.MWCB_LEVELS["LEVEL_3"]:
            return self._trigger_mwcb(
                level=3, 
                action="CLOSE_MARKET_FOR_DAY"
            )
        elif abs(decline) >= self.MWCB_LEVELS["LEVEL_2"]:
            return self._trigger_mwcb(
                level=2, 
                action=self._determine_halt_duration(time.now())
            )
        elif abs(decline) >= self.MWCB_LEVELS["LEVEL_1"]:
            return self._trigger_mwcb(
                level=1, 
                action=self._determine_halt_duration(time.now())
            )
        
        return {"status": "NORMAL"}
    
    def check_stock_circuit_limit(
        self,
        symbol: str,
        current_price: float,
        previous_close: float
    ) -> dict:
        """
        Check if stock hits circuit limit (upper or lower).
        
        Key Rules:
        - F&O stocks: No circuit limits (price discovery needed)
        - Non-F&O stocks: 2%, 5%, 10%, or 20% bands
        - At circuit: Only one-sided trading allowed
        """
        # Get stock's price band
        price_band = self.circuit_limits.get(symbol, self.PRICE_BANDS["10_PERCENT"])
        
        if price_band is None:
            return {"status": "NO_CIRCUIT", "reason": "F&O_STOCK"}
        
        price_change = (current_price - previous_close) / previous_close
        
        if price_change >= price_band:
            # Upper circuit hit
            self.halted_stocks.add(symbol)
            return {
                "status": "UPPER_CIRCUIT_HIT",
                "upper_limit": previous_close * (1 + price_band),
                "trading_allowed": "SELL_ONLY",  # Only sellers can trade
                "message": f"{symbol} locked at upper circuit {price_band*100}%"
            }
        
        elif price_change <= -price_band:
            # Lower circuit hit
            self.halted_stocks.add(symbol)
            return {
                "status": "LOWER_CIRCUIT_HIT",
                "lower_limit": previous_close * (1 - price_band),
                "trading_allowed": "BUY_ONLY",  # Only buyers can trade
                "message": f"{symbol} locked at lower circuit {price_band*100}%"
            }
        
        return {"status": "WITHIN_LIMITS"}
    
    def prevent_order_at_circuit(self, symbol: str, side: str) -> bool:
        """
        Prevent order placement when stock is circuit-locked.
        
        Critical: If stock hits circuit before auto-square-off:
        - Intraday position CANNOT be squared off
        - Converts to delivery (CNC/NRML)
        - Trader faces auction penalties if no funds/shares
        """
        if symbol in self.halted_stocks:
            logger.warning(
                f"Order rejected: {symbol} is circuit-locked. "
                f"Cannot place {side} order."
            )
            return False
        return True
    
    async def monitor_circuit_status(self):
        """
        Real-time monitoring of circuit breaker status.
        Send alerts when circuits are hit.
        """
        while True:
            # Check MWCB status from exchange feed
            # Check individual stock circuits
            # Update halted_stocks set
            # Broadcast alerts via WebSocket
            await asyncio.sleep(1)
```

**Critical Implications:**

If a stock hits circuit limit before broker's auto square-off time (3:10-3:25 PM), the intraday trade cannot be closed and converts to delivery, potentially causing significant losses or auction penalties.

**System Integrations:**
- Block order placement when stock is circuit-locked
- Auto-exit positions approaching circuit levels (risk management)
- Alert traders when circuits are imminent
- Handle MWCB market halts (pause all strategies)

---

## PART 2: ORDER TYPES & PRODUCT CODES

### 2.1 Product Type Support (MIS, CNC, NRML)

**Status:** 🟡 **BASIC IMPLEMENTATION NEEDED**

Indian brokers require product type selection for every order: MIS (intraday with leverage), CNC (delivery for equity), NRML (overnight F&O positions).

**Required Implementation:**

```python
# src/orders/product_types.py
from enum import Enum

class ProductType(Enum):
    """
    Indian market product types.
    Each product type has different margin and settlement rules.
    """
    
    MIS = "MIS"  # Margin Intraday Square-off
    CNC = "CNC"  # Cash and Carry (Delivery)
    NRML = "NRML"  # Normal (Overnight F&O)
    BO = "BO"  # Bracket Order (discontinued by most brokers)
    CO = "CO"  # Cover Order (discontinued by most brokers)

class ProductTypeManager:
    """
    Manages product type selection and margin calculation.
    """
    
    def __init__(self):
        self.auto_square_off_time = datetime.time(15, 20)  # 3:20 PM
        self.mis_leverage = {
            "EQUITY": 5.0,  # Example: 5x leverage for equity intraday
            "FNO": 1.0,  # F&O already leveraged via margins
        }
    
    def select_product_type(
        self,
        segment: str,  # "EQUITY" or "FNO"
        holding_period: str,  # "INTRADAY" or "DELIVERY" or "OVERNIGHT"
        intent: str  # "AUTO" or "MANUAL"
    ) -> ProductType:
        """
        Auto-select appropriate product type based on trade parameters.
        
        Rules:
        - Intraday equity: MIS (with leverage)
        - Delivery equity: CNC (full payment required)
        - Intraday F&O: MIS (optional, for higher leverage)
        - Overnight F&O: NRML (mandatory)
        """
        if segment == "EQUITY":
            if holding_period == "INTRADAY":
                return ProductType.MIS
            else:  # DELIVERY
                return ProductType.CNC
        
        elif segment == "FNO":
            if holding_period == "OVERNIGHT":
                return ProductType.NRML
            else:  # INTRADAY
                return ProductType.MIS  # Optional higher leverage
        
        raise ValueError(f"Invalid segment/holding combination")
    
    def calculate_margin_requirement(
        self,
        symbol: str,
        quantity: int,
        price: float,
        product_type: ProductType,
        segment: str
    ) -> float:
        """
        Calculate required margin based on product type.
        
        Margin Rules:
        - MIS (Equity): ~20% of trade value (5x leverage)
        - CNC: 100% of trade value (no leverage)
        - NRML (F&O): Full SPAN + Exposure margin
        - MIS (F&O): Reduced margin (broker-specific)
        """
        trade_value = quantity * price
        
        if product_type == ProductType.CNC:
            # No leverage for delivery
            return trade_value
        
        elif product_type == ProductType.MIS:
            if segment == "EQUITY":
                leverage = self.mis_leverage["EQUITY"]
                return trade_value / leverage
            else:  # F&O
                # Broker provides additional leverage on top of exchange margin
                base_margin = self._get_exchange_margin(symbol, quantity)
                return base_margin * 0.4  # Example: 40% of NRML margin
        
        elif product_type == ProductType.NRML:
            # Full exchange margin required
            return self._get_exchange_margin(symbol, quantity)
    
    async def auto_square_off_mis_positions(self):
        """
        Auto square-off MIS positions before market close.
        
        Critical Timing:
        - Most brokers: 3:10 PM - 3:25 PM
        - Market close: 3:30 PM
        - Conversion to CNC/NRML if not squared off
        """
        current_time = datetime.now().time()
        
        if current_time >= self.auto_square_off_time:
            mis_positions = await self.get_open_mis_positions()
            
            for position in mis_positions:
                try:
                    await self.square_off_position(position)
                    logger.info(f"Auto squared-off MIS position: {position['symbol']}")
                except Exception as e:
                    logger.error(
                        f"Failed to square-off {position['symbol']}: {e}. "
                        f"Position will convert to CNC/NRML."
                    )
    
    def convert_mis_to_cnc_nrml(self, position: dict) -> dict:
        """
        Convert MIS position to CNC/NRML (requires additional margin).
        
        Use Case: Trader wants to carry forward intraday position.
        Requirement: Must have sufficient margin in account.
        """
        additional_margin_required = self._calculate_conversion_margin(position)
        
        if self.available_margin < additional_margin_required:
            raise InsufficientMarginError(
                f"Need ₹{additional_margin_required} to convert to delivery"
            )
        
        new_product_type = (
            ProductType.CNC if position["segment"] == "EQUITY" 
            else ProductType.NRML
        )
        
        return {
            **position,
            "product_type": new_product_type,
            "converted_at": datetime.now(),
        }
```

**Key Implications:**
- If MIS positions aren't squared off by broker's deadline (typically 3:10-3:25 PM), they auto-convert to delivery with additional margin requirements and potential penalties
- System must handle auto-square-off logic
- Alert users approaching square-off deadline
- Provide MIS-to-CNC/NRML conversion option

---

## PART 3: TECHNICAL ANALYSIS & STRATEGY REQUIREMENTS

### 3.1 Indian Market-Specific Technical Indicators

**Status:** 🟡 **BASIC INDICATORS PRESENT**

For intraday trading in Indian markets, the most effective indicators are VWAP, RSI, MACD, Bollinger Bands, EMA crossovers, and ADX, with specific parameter optimizations for NSE/BSE volatility.

**Required Indicator Library:**

```python
# src/indicators/indian_market_indicators.py
class IndianMarketIndicators:
    """
    Technical indicators optimized for Indian market conditions.
    """
    
    @staticmethod
    def vwap(bars: pd.DataFrame) -> pd.Series:
        """
        Volume Weighted Average Price - Critical for intraday.
        
        Usage in Indian Markets:
        - Price above VWAP: Bullish sentiment
        - Price below VWAP: Bearish sentiment
        - Entry/Exit reference point
        
        Best for: High-beta stocks (Reliance, HDFC Bank, Infosys)
        """
        typical_price = (bars['high'] + bars['low'] + bars['close']) / 3
        return (typical_price * bars['volume']).cumsum() / bars['volume'].cumsum()
    
    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index - Momentum oscillator.
        
        Indian Market Settings:
        - Period: 14 (standard)
        - Overbought: 70
        - Oversold: 30
        - Intraday: Use 5-min or 15-min charts
        
        Caution: Stocks can remain overbought/oversold for extended periods
        """
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def supertrend(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 10,
        multiplier: float = 3.0
    ) -> tuple[pd.Series, pd.Series]:
        """
        Supertrend Indicator - Popular in Indian retail trading.
        
        Indian Market Usage:
        - Trend identification
        - Stop-loss placement
        - Trend reversal signals
        
        Settings:
        - Period: 10
        - Multiplier: 3.0 (standard)
        - Works well on Nifty 50, Bank Nifty
        """
        atr = ta.atr(high, low, close, period)
        hl_avg = (high + low) / 2
        
        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)
        
        # Supertrend calculation logic
        # Returns (supertrend_line, signal)
        pass
    
    @staticmethod
    def pivot_points(
        previous_high: float,
        previous_low: float,
        previous_close: float
    ) -> dict:
        """
        Pivot Points - Critical for intraday support/resistance.
        
        Indian Market Usage:
        - Calculate from previous day's H/L/C
        - Used heavily by NSE intraday traders
        - Resistance/Support levels for day
        
        Formula:
        - Pivot = (H + L + C) / 3
        - R1 = (2 * Pivot) - L
        - S1 = (2 * Pivot) - H
        """
        pivot = (previous_high + previous_low + previous_close) / 3
        
        r1 = (2 * pivot) - previous_low
        r2 = pivot + (previous_high - previous_low)
        r3 = r1 + (previous_high - previous_low)
        
        s1 = (2 * pivot) - previous_high
        s2 = pivot - (previous_high - previous_low)
        s3 = s1 - (previous_high - previous_low)
        
        return {
            "pivot": pivot,
            "r1": r1, "r2": r2, "r3": r3,
            "s1": s1, "s2": s2, "s3": s3,
        }
    
    @staticmethod
    def opening_range_breakout(
        bars: pd.DataFrame,
        or_period_minutes: int = 15
    ) -> dict:
        """
        Opening Range Breakout - Popular Indian intraday strategy.
        
        Methodology:
        - Identify high/low of first 15/30 minutes
        - Breakout above high = Buy signal
        - Breakdown below low = Sell signal
        
        Best for: Volatile stocks, Nifty/Bank Nifty
        Timeframe: First 15-30 minutes of trading
        """
        or_bars = bars.iloc[:or_period_minutes]
        or_high = or_bars['high'].max()
        or_low = or_bars['low'].min()
        
        return {
            "or_high": or_high,
            "or_low": or_low,
            "or_range": or_high - or_low,
        }
```

**Pre-Built Strategy Templates Needed:**

1. **Intraday Scalping (1-5 min holding)**
   - VWAP + Volume Spike
   - 5-EMA / 20-EMA crossover
   - Target: 0.5-1% per trade

2. **Intraday Momentum (15-60 min holding)**
   - RSI + MACD confirmation
   - Supertrend for trend direction
   - Target: 1-3% per trade

3. **Swing Trading (2-10 days holding)**
   - 20 EMA + 50 EMA crossover
   - RSI divergence
   - Fibonacci retracements
   - Target: 5-15% per trade

4. **Positional Trading (weeks to months)**
   - 50 SMA + 200 SMA (Golden/Death Cross)
   - Fundamental screening
   - Trend-following approach
   - Target: 15-50% per trade

---

### 3.2 Multi-Timeframe Analysis Support

**Status:** 🔴 **MISSING**

**Required Implementation:**

```python
# src/strategies/multi_timeframe.py
class MultiTimeframeStrategy(Strategy):
    """
    Analyze multiple timeframes for better accuracy.
    
    Common Indian Market Combinations:
    - Intraday: 1-min (entry) + 5-min (trend) + 15-min (confirmation)
    - Swing: 15-min + 1-hour + Daily
    - Positional: Daily + Weekly + Monthly
    """
    
    def __init__(self):
        self.timeframes = {
            "1MIN": "1-T",
            "5MIN": "5-T",
            "15MIN": "15-T",
            "1HOUR": "60-T",
            "DAILY": "1-D",
        }
        self.higher_timeframe_trend = None
    
    async def analyze_multiple_timeframes(self, symbol: str):
        """
        Check trend across multiple timeframes.
        
        Rule: Only trade in direction of higher timeframe trend.
        Example: If daily = uptrend, only take LONG on 5-min
        """
        # Get daily trend
        daily_bars = await self.get_bars(symbol, "DAILY")
        daily_trend = self.identify_trend(daily_bars)
        
        # Get hourly confirmation
        hourly_bars = await self.get_bars(symbol, "1HOUR")
        hourly_trend = self.identify_trend(hourly_bars)
        
        # Get entry timeframe signal
        entry_bars = await self.get_bars(symbol, "5MIN")
        entry_signal = self.generate_signal(entry_bars)
        
        # Confirm all timeframes align
        if daily_trend == hourly_trend == entry_signal:
            return {
                "action": entry_signal,
                "confidence": "HIGH",
                "reason": "All timeframes aligned"
            }
        else:
            return {
                "action": "HOLD",
                "confidence": "LOW",
                "reason": "Timeframe divergence"
            }
```

---

## PART 4: RISK MANAGEMENT ENHANCEMENTS

### 4.1 Indian Market-Specific Risk Controls

**Status:** 🟡 **BASIC IMPLEMENTATION**

**Required Enhancements:**

```python
# src/risk/indian_market_risk.py
class IndianMarketRiskManager:
    """
    Risk management tailored for Indian market conditions.
    """
    
    def __init__(self):
        # SEBI margin requirements
        self.var_margin = 0  # Value at Risk
        self.elm_margin = 0  # Extreme Loss Margin
        self.span_margin = 0  # Standard Portfolio Analysis of Risk
        self.exposure_margin = 0
        
        # Position limits
        self.max_position_size_per_stock = 0.25  # 25% of capital
        self.max_open_positions = 5
        self.max_sector_exposure = 0.40  # 40% in single sector
        
        # Intraday specific
        self.max_intraday_loss = 0.02  # 2% daily stop-loss
        self.max_mis_leverage = 5.0
    
    def calculate_position_size_indian_method(
        self,
        capital: float,
        risk_per_trade: float,
        entry_price: float,
        stop_loss: float,
        instrument_type: str  # "EQUITY" or "FNO"
    ) -> int:
        """
        Position sizing for Indian markets.
        
        Indian Market Considerations:
        - Lot sizes for F&O (cannot buy fractional lots)
        - Minimum trade value (₹500-1000 typically)
        - Circuit limits (may prevent stop-loss execution)
        """
        risk_amount = capital * risk_per_trade
        risk_per_share = abs(entry_price - stop_loss)
        
        if instrument_type == "EQUITY":
            # Can buy any quantity
            quantity = int(risk_amount / risk_per_share)
            
            # Minimum trade value check
            if quantity * entry_price < 1000:
                quantity = int(1000 / entry_price)
        
        elif instrument_type == "FNO":
            # Must buy in lot sizes
            lot_size = self.get_lot_size(symbol)
            quantity_float = risk_amount / (risk_per_share * lot_size)
            quantity = int(quantity_float) * lot_size  # Round to lot size
        
        return quantity
    
    def validate_order_against_rms(self, order: dict) -> bool:
        """
        Validate order against broker RMS (Risk Management System).
        
        Common RMS Rejections:
        - AB2005: Insufficient funds/margin
        - AB1004: Position limit exceeded
        - AB1012: Order price outside valid range
        - AB1026: Order quantity exceeds lot size
        """
        # Check margins
        required_margin = self.calculate_margin_requirement(order)
        if required_margin > self.available_margin:
            raise RMSError("AB2005: Insufficient margin")
        
        # Check position limits
        current_positions = self.get_open_positions_count()
        if current_positions >= self.max_open_positions:
            raise RMSError("AB1004: Maximum positions exceeded")
        
        # Check price bands
        if not self.is_price_within_circuit(order["symbol"], order["price"]):
            raise RMSError("AB1012: Price outside circuit limits")
        
        return True
    
    def implement_trailing_stop_loss(
        self,
        entry_price: float,
        current_price: float,
        trailing_percent: float = 0.01  # 1%
    ) -> float:
        """
        Trailing stop-loss for profit protection.
        
        Indian Market Usage:
        - Intraday: 0.5-1% trailing SL
        - Swing: 1-2% trailing SL
        - Positional: 3-5% trailing SL
        """
        profit = current_price - entry_price
        
        if profit > 0:
            trailing_sl = current_price - (current_price * trailing_percent)
            return max(entry_price, trailing_sl)  # Never below entry
        
        return entry_price * 0.99  # Initial 1% SL
    
    def check_sector_concentration(self, new_symbol: str) -> bool:
        """
        Prevent over-concentration in single sector.
        
        Indian Market Sectors:
        - Banking & Financial Services
        - IT & Technology
        - Pharma
        - Auto & Auto Ancillary
        - FMCG
        - Metals & Mining
        - Energy (Oil & Gas)
        """
        sector = self.get_sector(new_symbol)
        current_sector_exposure = self.calculate_sector_exposure(sector)
        
        if current_sector_exposure >= self.max_sector_exposure:
            logger.warning(
                f"Sector exposure limit: {sector} = {current_sector_exposure:.1%}"
            )
            return False
        
        return True
```

---

## PART 5: DATA & MARKET MICROSTRUCTURE

### 5.1 Pre-Market & Post-Market Session Handling

**Status:** 🔴 **MISSING**

**Required Implementation:**

```python
# src/market/session_manager.py
class MarketSessionManager:
    """
    Handle different trading sessions in Indian markets.
    """
    
    SESSIONS = {
        "PRE_OPEN": {
            "start": datetime.time(9, 0),
            "end": datetime.time(9, 15),
            "description": "Pre-market session (call auction)"
        },
        "REGULAR": {
            "start": datetime.time(9, 15),
            "end": datetime.time(15, 30),
            "description": "Regular trading session"
        },
        "POST_MARKET": {
            "start": datetime.time(15, 30),
            "end": datetime.time(16, 0),
            "description": "Post-market session"
        }
    }
    
    def get_current_session(self) -> str:
        """Identify current market session."""
        now = datetime.now().time()
        
        for session_name, session_info in self.SESSIONS.items():
            if session_info["start"] <= now < session_info["end"]:
                return session_name
        
        return "CLOSED"
    
    def handle_pre_open_auction(self):
        """
        Pre-open session (9:00-9:15 AM):
        - Order collection: 9:00-9:08 AM
        - Order matching: 9:08-9:12 AM
        - Buffer period: 9:12-9:15 AM
        - Opening price determined via call auction
        
        Strategy Consideration: Pre-open prices can differ significantly
        from previous close, affecting gap-up/gap-down strategies.
        """
        pass
    
    def get_opening_range_data(self) -> dict:
        """
        Critical data for Indian intraday strategies.
        
        Opening Range Metrics:
        - Pre-market high/low
        - Opening price (9:15 AM)
        - First 15-min high/low
        - Opening gap (% vs previous close)
        """
        pass
```

---

## PART 6: MISSING UTILITY FEATURES

### 6.1 Options Chain Analysis (for F&O trading)

**Status:** 🔴 **MISSING - IMPORTANT**

```python
# src/fno/options_chain.py
class OptionsChainAnalyzer:
    """
    Analyze options chain for Nifty/Bank Nifty trading.
    Critical for understanding market sentiment.
    """
    
    def get_max_pain_theory(self, options_chain: dict) -> float:
        """
        Calculate max pain strike price.
        Price at which option sellers have minimum loss.
        """
        pass
    
    def calculate_put_call_ratio(self, options_chain: dict) -> float:
        """
        PCR Ratio = Put OI / Call OI
        
        Interpretation:
        - PCR > 1.0: Bullish (more puts written)
        - PCR < 0.7: Bearish (more calls written)
        
        Critical for Nifty/Bank Nifty direction.
        """
        pass
    
    def identify_option_strikes_with_high_oi(self, options_chain: dict):
        """
        High Open Interest strikes act as support/resistance.
        """
        pass
```

### 6.2 Corporate Actions Handler

**Status:** 🔴 **MISSING - IMPORTANT**

```python
# src/corporate/actions_handler.py
class CorporateActionsHandler:
    """
    Handle corporate actions affecting positions.
    
    Types:
    - Dividends (ex-date adjustments)
    - Stock splits
    - Bonus issues
    - Rights issues
    - Mergers & acquisitions
    """
    
    def adjust_positions_for_split(
        self,
        symbol: str,
        split_ratio: str  # e.g., "1:2" (1 share becomes 2)
    ):
        """
        Adjust positions and stop-losses after stock split.
        """
        pass
    
    def handle_dividend_ex_date(self, symbol: str, dividend_amount: float):
        """
        Adjust for dividend ex-date price drop.
        """
        pass
```

### 6.3 Tax Calculation (Indian Tax Rules)

**Status:** 🔴 **MISSING**

```python
# src/tax/indian_tax_calculator.py
class IndianTaxCalculator:
    """
    Calculate tax liability per Indian tax rules.
    
    Tax Rates (FY 2024-25):
    - Short-term capital gains (STCG):
      * Equity (held < 1 year): 15%
      * Debt (held < 3 years): As per slab
    
    - Long-term capital gains (LTCG):
      * Equity (held > 1 year): 10% above ₹1 lakh
      * Debt (held > 3 years): 20% with indexation
    
    - Intraday/F&O: Treated as speculative business income
      * Taxed as per income tax slab (up to 30%)
    
    - STT (Securities Transaction Tax): Auto-deducted
    """
    
    def calculate_tax_liability(
        self,
        trades: list,
        holding_period: str,
        trader_income_slab: float
    ) -> dict:
        """Calculate total tax liability."""
        pass
    
    def generate_tax_pnl_report(self, financial_year: str):
        """Generate P&L statement for ITR filing."""
        pass
```

---

## PART 7: PERFORMANCE & MONITORING

### 7.1 Indian Market-Specific Metrics

**Required Metrics Dashboard:**

```python
# src/analytics/indian_market_metrics.py
class IndianMarketMetrics:
    """
    Performance metrics for Indian market trading.
    """
    
    def calculate_sharpe_ratio_india(
        self,
        returns: pd.Series,
        risk_free_rate: float = 0.07  # Indian 10Y G-Sec yield
    ) -> float:
        """
        Sharpe Ratio using Indian risk-free rate.
        """
        excess_returns = returns - (risk_free_rate / 252)
        return excess_returns.mean() / excess_returns.std() * np.sqrt(252)
    
    def calculate_nifty_beta(self, stock_returns: pd.Series) -> float:
        """
        Calculate stock's beta vs Nifty 50.
        Measures volatility relative to market.
        """
        pass
    
    def track_brokerage_costs(self):
        """
        Track all-in costs for Indian trading:
        - Brokerage (₹20 or 0.03% whichever lower for discount brokers)
        - STT (0.025% for delivery, 0.025% on sell for intraday)
        - Transaction charges (NSE/BSE)
        - GST (18% on brokerage)
        - SEBI turnover charges
        - Stamp duty (state-specific)
        
        Total cost: ~0.3-0.6% per trade
        """
        pass
```

---

## SUMMARY OF CRITICAL MISSING REQUIREMENTS

### Regulatory & Compliance (MANDATORY)
1. ✅ **SEBI Algo Registration** - Exchange approval + Algo ID tagging
2. ✅ **Static IP Whitelisting** - 2FA authentication
3. ✅ **Audit Trail** - 5-year detailed logs
4. ✅ **OPS Monitoring** - 10 orders/sec threshold

### Market Mechanics (CRITICAL)
5. ✅ **Settlement Cycle** - T+1 / T+0 handling
6. ✅ **Circuit Breakers** - MWCB + stock price bands
7. ✅ **Product Types** - MIS/CNC/NRML support
8. ✅ **Auto Square-Off** - Pre-close position management

### Trading Strategies (HIGH PRIORITY)
9. ✅ **Indian Indicators** - VWAP, Supertrend, Pivot Points, ORB
10. ✅ **Multi-Timeframe** - Trend confirmation across timeframes
11. ✅ **Pre-Built Strategies** - Intraday/Swing/Positional templates

### Risk Management (CRITICAL)
12. ✅ **Position Sizing** - Lot-size aware for F&O
13. ✅ **Sector Limits** - Concentration risk management
14. ✅ **RMS Validation** - Pre-trade compliance checks
15. ✅ **Trailing SL** - Dynamic stop-loss management

### Data & Analytics (IMPORTANT)
16. ✅ **Session Management** - Pre-market/Post-market handling
17. ✅ **Options Chain** - PCR, Max Pain analysis (for F&O)
18. ✅ **Corporate Actions** - Splits, dividends adjustment
19. ✅ **Tax Calculation** - STCG/LTCG computation

### System Infrastructure (IMPORTANT)
20. ✅ **Broker Outage Handling** - Fallback mechanisms
21. ✅ **Exchange Connectivity** - Multiple exchange support (NSE/BSE/MCX)
22. ✅ **Data Quality Checks** - Tick validation, missing data handling

---

## IMPLEMENTATION PRIORITY

**Phase 1: Regulatory Compliance (Weeks 1-2)**
- SEBI algo registration
- Static IP setup
- Audit trail implementation
- **Blocker:** Cannot go live without this

**Phase 2: Critical Market Mechanics (Weeks 3-4)**
- Circuit breaker handling
- Product type support (MIS/CNC/NRML)
- Settlement cycle management
- Auto square-off logic

**Phase 3: Risk & Strategy (Weeks 5-7)**
- Indian market indicators
- Position sizing for F&O
- Multi-timeframe analysis
- Pre-built strategy templates

**Phase 4: Advanced Features (Weeks 8-10)**
- Options chain analysis
- Corporate actions
- Tax calculation
- Performance analytics

---

## CONCLUSION

This system requires **significant enhancements** beyond the base architecture to be production-ready for the Indian stock market. The SEBI 2025 regulations alone introduce mandatory compliance requirements that cannot be bypassed.

**Estimated Additional Development:** 8-10 weeks  
**Risk Level Without Compliance:** 🔴 **CRITICAL - System will be rejected by brokers**

**Next Steps:**
1. Prioritize SEBI compliance implementation
2. Add circuit breaker and product type support
3. Implement Indian market-specific indicators
4. Test with paper trading for 2-4 weeks
5. Obtain broker approval before live deployment

---

**Document Version:** 1.0  
**Last Updated:** February 2026  
**Regulatory Reference:** SEBI/HO/MIRSD/MIRSD-PoD1/P/CIR/2024/169
