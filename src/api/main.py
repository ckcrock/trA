from contextlib import asynccontextmanager
import inspect
import json
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from src.api.dependencies import (
    get_auth_manager,
    get_data_bridge,
    get_execution_client,
    get_health_checker,
    get_lifecycle_manager,
    get_symbol_resolver,
    get_trading_node,
    get_ws_client,
)
from src.api.routes import instruments, market_data, orders, positions, strategies, websocket
from src.api.routes.strategies import set_lifecycle_manager
from src.api.routes.websocket import manager as ui_ws_manager
from src.api.services.background_tasks import BackgroundTaskManager
from src.bridge.websocket_broadcaster import WebSocketBroadcaster
from src.observability.logging_config import setup_logging
from src.observability.metrics import init_metrics

setup_logging()
logger = logging.getLogger("api")


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Starting up Trading Platform API")

        bg_tasks = BackgroundTaskManager()
        ws_broadcaster = WebSocketBroadcaster(ui_ws_manager)
        app.state.bg_tasks = bg_tasks

        init_metrics()

        bridge = get_data_bridge()
        auth = get_auth_manager()
        ws_client = get_ws_client()
        _ = get_symbol_resolver()
        health = get_health_checker()
        node = get_trading_node()

        lifecycle = get_lifecycle_manager()
        set_lifecycle_manager(lifecycle)

        await bridge.start()
        maybe_subscribe = bridge.subscribe(ws_broadcaster.broadcast_tick)
        if inspect.isawaitable(maybe_subscribe):
            await maybe_subscribe
        health.update_component("data_bridge", "healthy")

        def bridge_callback(tick):
            bridge.submit_tick(tick)

        ws_client.register_callback(bridge_callback)
        if os.getenv("ENABLE_BROKER_WS", "false").lower() == "true":
            ws_client.connect_in_thread()
            logger.info("Broker WebSocket connection thread started")
            default_tokens_raw = os.getenv("BROKER_DEFAULT_SUBSCRIPTIONS", "")
            if default_tokens_raw:
                try:
                    token_list = json.loads(default_tokens_raw)
                    mode = int(os.getenv("BROKER_WS_MODE", "1"))
                    ws_client.subscribe(mode=mode, token_list=token_list)
                    logger.info("Broker WebSocket subscribed to %s token groups", len(token_list))
                except Exception as e:
                    logger.error("Failed broker WS subscription bootstrap: %s", e)
        else:
            logger.info("Broker WebSocket bootstrap disabled (ENABLE_BROKER_WS=false)")

        await node.start()
        health.update_component("trading_node", "healthy")

        bg_tasks.auth = auth
        bg_tasks.execution = get_execution_client()
        bg_tasks.health = health
        await bg_tasks.start()

        logger.info("Startup complete")

        try:
            yield
        finally:
            logger.info("Shutting down")
            await bg_tasks.stop()
            await get_data_bridge().stop()
            await get_trading_node().stop()
            get_ws_client().close()
            logger.info("Shutdown complete")

    app = FastAPI(
        title="Hybrid Trading Platform API",
        version="1.0.0",
        description="Indian market trading platform with Angel One integration",
        docs_url="/api/docs",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    app.include_router(websocket.router, tags=["websocket"])
    app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
    app.include_router(positions.router, prefix="/api/positions", tags=["positions"])
    app.include_router(instruments.router, prefix="/api/instruments", tags=["instruments"])
    app.include_router(market_data.router, prefix="/api/market", tags=["market_data"])
    app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])

    @app.get("/health")
    async def health_check():
        checker = get_health_checker()
        return checker.get_health()

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)

