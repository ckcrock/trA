class WSManager {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.callbacks = {};
        this.subscriptions = new Set();
        this.reconnectAttempts = 0;
        this.shouldReconnect = true;
    }

    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            return;
        }

        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            this.reconnectAttempts = 0;
            this._emit("open");
            this.subscriptions.forEach((channel) => this._sendSubscribe(channel));
        };

        this.ws.onmessage = (event) => {
            let message;
            try {
                message = JSON.parse(event.data);
            } catch (error) {
                this._emit("error", new Error("Invalid WebSocket payload"));
                return;
            }

            this._emit("message", message);
            if (message && message.type) {
                this._emit(message.type, message.data);
            }
        };

        this.ws.onerror = () => {
            this._emit("error", new Error("WebSocket connection error"));
        };

        this.ws.onclose = () => {
            this._emit("close");
            if (!this.shouldReconnect) {
                return;
            }
            this.reconnectAttempts += 1;
            const delay = Math.min(15000, 1000 * Math.pow(2, this.reconnectAttempts));
            setTimeout(() => this.connect(), delay);
        };
    }

    close() {
        this.shouldReconnect = false;
        if (this.ws) {
            this.ws.close();
        }
    }

    subscribe(channel) {
        if (!channel) {
            return;
        }
        this.subscriptions.add(channel);
        this._sendSubscribe(channel);
    }

    on(eventType, callback) {
        if (!this.callbacks[eventType]) {
            this.callbacks[eventType] = [];
        }
        this.callbacks[eventType].push(callback);
    }

    _sendSubscribe(channel) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(
                JSON.stringify({
                    action: "subscribe",
                    channel,
                })
            );
        }
    }

    _emit(eventType, payload) {
        const handlers = this.callbacks[eventType] || [];
        handlers.forEach((handler) => {
            try {
                handler(payload);
            } catch (error) {
                // Keep emitter resilient to subscriber exceptions.
                console.error("WebSocket handler error:", error);
            }
        });
    }
}

window.WSManager = WSManager;
