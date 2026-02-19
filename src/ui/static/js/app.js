const DEFAULT_HOST = "localhost:8000";
const APP_HOST = window.location.host || DEFAULT_HOST;
const API_BASE = `${window.location.protocol || "http:"}//${APP_HOST}`;
const WS_PROTOCOL = (window.location.protocol || "http:") === "https:" ? "wss" : "ws";
const WS_URL = `${WS_PROTOCOL}://${APP_HOST}/ws/stream`;

const DEFAULT_WATCHLIST = [
    { symbol: "SBIN-EQ", exchange: "NSE" },
    { symbol: "RELIANCE-EQ", exchange: "NSE" },
    { symbol: "INFY-EQ", exchange: "NSE" },
    { symbol: "ICICIBANK-EQ", exchange: "NSE" },
];

const state = {
    selectedSymbol: "SBIN-EQ",
    selectedExchange: "NSE",
    timeframeSec: 60,
    watchlist: new Map(),
    tickTimestamps: [],
    tickHistoryBySymbol: new Map(),
    latestBySymbol: new Map(),
};

let chart;
let candleSeries;
let wsManager;
let resizeObserver;

function byId(id) {
    return document.getElementById(id);
}

function init() {
    initClock();
    initWatchlist();
    initChart();
    initControls();
    initWebSocket();
    refreshPositions();
    refreshHealth();

    setInterval(updateTickRate, 1000);
    setInterval(refreshPositions, 15000);
    setInterval(refreshHealth, 10000);
}

function initClock() {
    const clockEl = byId("clock");
    const render = () => {
        clockEl.textContent = new Date().toLocaleTimeString();
    };
    render();
    setInterval(render, 1000);
}

function initWatchlist() {
    DEFAULT_WATCHLIST.forEach((item) => {
        state.watchlist.set(item.symbol, {
            symbol: item.symbol,
            exchange: item.exchange,
            price: null,
            basePrice: null,
            changePct: 0,
            token: null,
        });
    });
    renderWatchlist();
}

function renderWatchlist() {
    const list = byId("watchlist");
    list.innerHTML = "";
    [...state.watchlist.values()].forEach((item) => {
        const li = document.createElement("li");
        li.className = "watch-item";
        if (item.symbol === state.selectedSymbol) {
            li.classList.add("active");
        }
        li.dataset.symbol = item.symbol;
        li.innerHTML = `
            <div class="watch-symbol">${item.symbol}</div>
            <div class="watch-price">${item.price === null ? "--" : item.price.toFixed(2)}</div>
            <div class="watch-change ${item.changePct >= 0 ? "up" : "down"}">${formatPct(item.changePct)}</div>
        `;
        li.addEventListener("click", () => {
            state.selectedSymbol = item.symbol;
            state.selectedExchange = item.exchange;
            byId("order-symbol").value = item.symbol;
            byId("order-exchange").value = item.exchange;
            byId("active-symbol").textContent = item.symbol;
            renderWatchlist();
            rebuildSelectedSeries();
        });
        list.appendChild(li);
    });
}

function formatPct(value) {
    const sign = value >= 0 ? "+" : "";
    return `${sign}${value.toFixed(2)}%`;
}

function initChart() {
    const chartContainer = byId("tv-chart-container");
    chart = LightweightCharts.createChart(chartContainer, {
        layout: {
            background: { color: "transparent" },
            textColor: "#e9f0ff",
            fontFamily: "'Space Grotesk', sans-serif",
        },
        grid: {
            vertLines: { color: "rgba(171, 194, 255, 0.08)" },
            horzLines: { color: "rgba(171, 194, 255, 0.08)" },
        },
        rightPriceScale: {
            borderColor: "rgba(171, 194, 255, 0.25)",
        },
        timeScale: {
            borderColor: "rgba(171, 194, 255, 0.25)",
            timeVisible: true,
            secondsVisible: false,
        },
    });

    candleSeries = chart.addCandlestickSeries({
        upColor: "#14d29c",
        downColor: "#f26b5e",
        borderUpColor: "#14d29c",
        borderDownColor: "#f26b5e",
        wickUpColor: "#14d29c",
        wickDownColor: "#f26b5e",
    });

    resizeObserver = new ResizeObserver((entries) => {
        if (!entries.length) {
            return;
        }
        const rect = entries[0].contentRect;
        chart.applyOptions({
            width: rect.width,
            height: rect.height,
        });
    });
    resizeObserver.observe(chartContainer);
}

function initControls() {
    byId("active-symbol").textContent = state.selectedSymbol;
    byId("order-symbol").value = state.selectedSymbol;
    byId("order-exchange").value = state.selectedExchange;

    byId("symbol-search").addEventListener("input", (event) => {
        const term = event.target.value.trim().toUpperCase();
        const items = document.querySelectorAll(".watch-item");
        items.forEach((item) => {
            const symbol = item.dataset.symbol || "";
            item.style.display = symbol.includes(term) ? "" : "none";
        });
    });

    document.querySelectorAll(".timeframe-btn").forEach((button) => {
        button.addEventListener("click", () => {
            document.querySelectorAll(".timeframe-btn").forEach((b) => b.classList.remove("active"));
            button.classList.add("active");
            state.timeframeSec = Number(button.dataset.seconds || 60);
            rebuildSelectedSeries();
        });
    });

    byId("order-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        await placeOrder();
    });
}

function initWebSocket() {
    wsManager = new WSManager(WS_URL);

    wsManager.on("open", () => {
        setConnectionStatus("Connected", "connected");
        wsManager.subscribe("market_data");
    });

    wsManager.on("close", () => {
        setConnectionStatus("Disconnected", "disconnected");
    });

    wsManager.on("error", () => {
        setConnectionStatus("Connection Error", "degraded");
    });

    wsManager.on("TICK", (tick) => {
        if (!tick) {
            return;
        }

        state.tickTimestamps.push(Date.now());
        pruneTickRateWindow();

        const symbol = resolveTickSymbol(tick);
        const price = Number(tick.ltp || 0);
        if (!price || Number.isNaN(price)) {
            return;
        }

        updateWatchSymbol(symbol, tick, price);
        pushTickHistory(symbol, tick.timestamp, price);
        updateActiveDisplay(symbol, price);
        updateTape(symbol, price, tick.timestamp);

        if (symbol === state.selectedSymbol) {
            rebuildSelectedSeries();
        }
    });

    wsManager.connect();
}

function setConnectionStatus(text, stateClass) {
    const el = byId("connection-status");
    el.textContent = text;
    el.classList.remove("connected", "disconnected", "degraded");
    el.classList.add(stateClass);
}

function pruneTickRateWindow() {
    const cutoff = Date.now() - 60000;
    state.tickTimestamps = state.tickTimestamps.filter((ts) => ts >= cutoff);
}

function updateTickRate() {
    pruneTickRateWindow();
    byId("tick-rate").textContent = `${state.tickTimestamps.length} ticks/min`;
}

function resolveTickSymbol(tick) {
    if (tick.symbol && tick.symbol !== "UNKNOWN") {
        return String(tick.symbol).toUpperCase();
    }
    if (tick.token) {
        return `TOKEN-${tick.token}`;
    }
    return "UNKNOWN";
}

function updateWatchSymbol(symbol, tick, price) {
    if (!state.watchlist.has(symbol)) {
        state.watchlist.set(symbol, {
            symbol,
            exchange: state.selectedExchange,
            price: null,
            basePrice: null,
            changePct: 0,
            token: tick.token || null,
        });
    }

    const entry = state.watchlist.get(symbol);
    if (entry.basePrice === null) {
        entry.basePrice = price;
    }
    entry.price = price;
    entry.changePct = entry.basePrice ? ((price - entry.basePrice) / entry.basePrice) * 100 : 0;
    entry.token = tick.token || entry.token;

    state.latestBySymbol.set(symbol, { price, timestamp: tick.timestamp });
    renderWatchlist();
}

function pushTickHistory(symbol, timestamp, price) {
    const ts = Number.isFinite(Date.parse(timestamp)) ? new Date(timestamp).getTime() : Date.now();
    const history = state.tickHistoryBySymbol.get(symbol) || [];
    history.push({ ts, price });
    if (history.length > 5000) {
        history.splice(0, history.length - 5000);
    }
    state.tickHistoryBySymbol.set(symbol, history);
}

function updateActiveDisplay(symbol, price) {
    if (symbol !== state.selectedSymbol) {
        return;
    }
    byId("active-price").textContent = price.toFixed(2);
}

function updateTape(symbol, price, timestamp) {
    const tape = byId("market-tape");
    const item = document.createElement("div");
    item.className = "tape-item";
    const time = Number.isFinite(Date.parse(timestamp))
        ? new Date(timestamp).toLocaleTimeString()
        : new Date().toLocaleTimeString();
    item.textContent = `${time} ${symbol} ${price.toFixed(2)}`;
    tape.prepend(item);
    while (tape.children.length > 25) {
        tape.removeChild(tape.lastChild);
    }
}

function buildCandles(history, bucketSeconds) {
    if (!history || !history.length) {
        return [];
    }

    const candles = [];
    let current = null;
    history.forEach((point) => {
        const bucketStart = Math.floor(point.ts / (bucketSeconds * 1000)) * bucketSeconds;
        if (!current || current.time !== bucketStart) {
            current = {
                time: bucketStart,
                open: point.price,
                high: point.price,
                low: point.price,
                close: point.price,
            };
            candles.push(current);
            return;
        }

        current.high = Math.max(current.high, point.price);
        current.low = Math.min(current.low, point.price);
        current.close = point.price;
    });
    return candles.slice(-400);
}

function rebuildSelectedSeries() {
    const history = state.tickHistoryBySymbol.get(state.selectedSymbol) || [];
    const candles = buildCandles(history, state.timeframeSec);
    candleSeries.setData(candles);
}

async function resolveInstrument(symbol, exchange) {
    const url = `${API_BASE}/api/instruments/resolve?symbol=${encodeURIComponent(symbol)}&exchange=${encodeURIComponent(exchange)}`;
    const response = await fetch(url);
    if (!response.ok) {
        return null;
    }
    return response.json();
}

async function placeOrder() {
    const orderStatus = byId("order-status");
    orderStatus.textContent = "Placing order...";
    orderStatus.className = "order-status pending";

    const symbol = byId("order-symbol").value.trim().toUpperCase();
    const exchange = byId("order-exchange").value;
    const side = byId("order-side").value;
    const orderType = byId("order-type").value;
    const product = byId("order-product").value;
    const quantity = Number(byId("order-qty").value || 0);
    const rawPrice = Number(byId("order-price").value || 0);

    if (!symbol || quantity <= 0) {
        orderStatus.textContent = "Invalid symbol or quantity.";
        orderStatus.className = "order-status error";
        return;
    }

    try {
        const instrument = await resolveInstrument(symbol, exchange);
        if (!instrument || !instrument.token) {
            orderStatus.textContent = "Instrument token not found.";
            orderStatus.className = "order-status error";
            return;
        }

        const latest = state.latestBySymbol.get(symbol);
        const marketReference = rawPrice || (latest ? latest.price : 0);

        const payload = {
            tradingsymbol: instrument.symbol || symbol,
            symboltoken: String(instrument.token),
            transactiontype: side,
            exchange,
            ordertype: orderType,
            producttype: product,
            duration: "DAY",
            price: orderType === "MARKET" ? marketReference : rawPrice,
            quantity,
            triggerprice: null,
            variety: "NORMAL",
        };

        const response = await fetch(`${API_BASE}/api/orders/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await response.json();

        if (!response.ok) {
            const detail = data?.detail?.message || data?.detail || "Order rejected";
            throw new Error(detail);
        }

        orderStatus.textContent = `Order placed: ${data.order_id}`;
        orderStatus.className = "order-status success";
    } catch (error) {
        orderStatus.textContent = `Order failed: ${error.message}`;
        orderStatus.className = "order-status error";
    }
}

function toNumber(value) {
    const num = Number(value);
    return Number.isFinite(num) ? num : 0;
}

async function refreshPositions() {
    const body = byId("positions-body");
    try {
        const response = await fetch(`${API_BASE}/api/positions/`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        const rows = Array.isArray(data?.net) ? data.net : [];

        if (!rows.length) {
            body.innerHTML = `<tr><td colspan="6" class="muted">No open positions</td></tr>`;
            return;
        }

        body.innerHTML = rows
            .map((pos) => {
                const symbol = pos.tradingsymbol || pos.symbol || "--";
                const qty = toNumber(pos.netqty || pos.quantity || 0);
                const avg = toNumber(pos.averageprice || pos.avg_price || 0);
                const ltp = toNumber(pos.ltp || pos.last_price || 0);
                const pnl = toNumber(pos.pnl || pos.unrealized || 0);
                const pnlClass = pnl >= 0 ? "up" : "down";
                return `
                    <tr>
                        <td>${symbol}</td>
                        <td>${qty}</td>
                        <td>${avg.toFixed(2)}</td>
                        <td>${ltp.toFixed(2)}</td>
                        <td class="${pnlClass}">${pnl.toFixed(2)}</td>
                        <td><button class="inline-btn">Monitor</button></td>
                    </tr>
                `;
            })
            .join("");
    } catch (error) {
        body.innerHTML = `<tr><td colspan="6" class="muted">Failed to load positions</td></tr>`;
    }
}

async function refreshHealth() {
    const queueSizeEl = byId("queue-size");
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (!response.ok) {
            return;
        }
        const health = await response.json();
        const queueSize = health?.components?.data_bridge?.queue_size;
        queueSizeEl.textContent = queueSize === undefined ? "--" : String(queueSize);
    } catch (error) {
        queueSizeEl.textContent = "--";
    }
}

window.addEventListener("beforeunload", () => {
    if (wsManager) {
        wsManager.close();
    }
    if (resizeObserver) {
        resizeObserver.disconnect();
    }
});

window.addEventListener("load", init);
