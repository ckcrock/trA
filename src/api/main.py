from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import asyncio
import logging

# Import Routes
from src.api.routes import websocket, orders, positions, instruments, market_data, strategies
from src.api.dependencies import (
    get_data_bridge, get_ws_client, get_auth_manager,
    get_symbol_resolver, get_health_checker, get_lifecycle_manager,
    get_data_client, get_execution_client, get_trading_node,
)

# Observability
from src.observability.logging_config import setup_logging
from src.observability.metrics import init_metrics
from src.observability.health_check import get_health_checker as _get_health

# Background tasks
from src.api.services.background_tasks import BackgroundTaskManager

# Strategy routes need lifecycle manager reference
from src.api.routes.strategies import set_lifecycle_manager

# Setup structured logging
setup_logging()
logger = logging.getLogger("api")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hybrid Trading Platform API",
        version="1.0.0",
        description="Indian market trading platform with Angel One integration",
        docs_url="/api/docs",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # Include routers
    app.include_router(websocket.router, tags=["websocket"])
    app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
    app.include_router(positions.router, prefix="/api/positions", tags=["positions"])
    app.include_router(instruments.router, prefix="/api/instruments", tags=["instruments"])
    app.include_router(market_data.router, prefix="/api/market", tags=["market_data"])
    app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        checker = get_health_checker()
        return checker.get_health()

    # Background task manager (stored on app state)
    bg_tasks = BackgroundTaskManager()

    @app.on_event("startup")
    async def startup():
        logger.info("🚀 Starting up Trading Platform API...")

        # 1. Initialize metrics
        init_metrics()

        # 2. Initialize Singletons
        bridge = get_data_bridge()
        auth = get_auth_manager()
        ws_client = get_ws_client()
        resolver = get_symbol_resolver()
        health = get_health_checker()
        node = get_trading_node()

        # 3. Wire strategy lifecycle
        # Note: get_lifecycle_manager() now returns node.lifecycle, ensuring consistency
        lifecycle = get_lifecycle_manager()
        set_lifecycle_manager(lifecycle)

        # 4. Start Data Bridge
        await bridge.start()
        health.update_component("data_bridge", "healthy")

        # 5. Connect Broker WebSocket → Data Bridge
        def bridge_callback(tick):
            bridge.submit_tick(tick)

        ws_client.register_callback(bridge_callback)
        
        # 6. Start Trading Node (Orchestrator)
        # This initializes Nautilus if available, or just prepares the lifecycle manager
        await node.start()
        health.update_component("trading_node", "healthy")

        # 7. Start background tasks
        bg_tasks.auth = auth
        bg_tasks.execution = get_execution_client()
        bg_tasks.health = health
        await bg_tasks.start()

        logger.info("✅ Startup complete.")

    @app.on_event("shutdown")
    async def shutdown():
        logger.info("⏹️ Shutting down...")
        await bg_tasks.stop()
        await get_data_bridge().stop()
        await get_trading_node().stop()
        get_ws_client().close()
        logger.info("✅ Shutdown complete.")

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
