// Initialize WebSocket
const wsUrl = "ws://localhost:8000/ws/stream";
const wsManager = new WSManager(wsUrl);

// Initialize Chart
const chartDiv = document.getElementById('tv-chart-container');
const chart = LightweightCharts.createChart(chartDiv, {
    layout: {
        background: { color: '#17171c' }, // Match panel-bg
        textColor: '#ddd',
    },
    grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
    },
    crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
    },
    rightPriceScale: {
        borderColor: 'rgba(197, 203, 206, 0.8)',
    },
    timeScale: {
        borderColor: 'rgba(197, 203, 206, 0.8)',
        timeVisible: true,
        secondsVisible: false,
    },
});

const candleSeries = chart.addCandlestickSeries({
    upColor: '#00d06c',
    downColor: '#ff2800',
    borderVisible: false,
    wickUpColor: '#00d06c',
    wickDownColor: '#ff2800',
});

// Resize Observer
const resizeObserver = new ResizeObserver(entries => {
    if (entries.length === 0 || entries[0].target !== chartDiv) { return; }
    const newRect = entries[0].contentRect;
    chart.applyOptions({ height: newRect.height, width: newRect.width });
});

resizeObserver.observe(chartDiv);

// Connect WebSocket
wsManager.connect();

// Listen for Ticks
wsManager.on('TICK', (data) => {
    // Update Chart if symbol matches
    // Note: Data format needs to match what lightweight-charts expects (time, open, high, low, close)
    // We assume backend broadcasts normalized data

    // For demo, we just log
    // console.log("Tick:", data);
});

// Clock
setInterval(() => {
    document.getElementById('clock').innerText = new Date().toLocaleTimeString();
}, 1000);
