class WSManager {
    constructor(url) {
        self.url = url;
        self.ws = null;
        self.callbacks = {}; // channel -> [callback]
    }

    connect() {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log("Connected to WebSocket");
            document.getElementById('connection-status').innerText = '🟢 Connected';
            document.getElementById('connection-status').style.color = '#00d06c';
            
            // Subscribe to default channels
            this.subscribe("market_data");
        };

        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };

        this.ws.onclose = () => {
            console.log("Disconnected from WebSocket");
            document.getElementById('connection-status').innerText = '🔴 Disconnected';
            document.getElementById('connection-status').style.color = '#ff2800';
            
            // Auto reconnect
            setTimeout(() => this.connect(), 5000);
        };
    }

    subscribe(channel) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                action: "subscribe",
                channel: channel
            }));
        }
    }

    on(type, callback) {
        if (!this.callbacks[type]) {
            this.callbacks[type] = [];
        }
        this.callbacks[type].push(callback);
    }

    handleMessage(message) {
        // Dispatch to type-specific listeners
        if (message.type && this.callbacks[message.type]) {
            this.callbacks[message.type].forEach(cb => cb(message.data));
        }
    }
}
