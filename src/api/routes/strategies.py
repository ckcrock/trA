"""
Strategy control API routes.
Reference: SYSTEM_ARCHITECTURE.md §3.1
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Optional
from src.engine.lifecycle import StrategyLifecycleManager

router = APIRouter()

# Singleton lifecycle manager — will be set by app startup
_lifecycle: Optional[StrategyLifecycleManager] = None


def set_lifecycle_manager(manager: StrategyLifecycleManager):
    """Set the lifecycle manager instance (called during app startup)."""
    global _lifecycle
    _lifecycle = manager


def _get_lifecycle() -> StrategyLifecycleManager:
    if _lifecycle is None:
        raise HTTPException(status_code=503, detail="Strategy manager not initialized")
    return _lifecycle


@router.get("/")
async def list_strategies():
    """List all registered strategies and their status."""
    lc = _get_lifecycle()
    return lc.get_status()


@router.get("/{name}")
async def get_strategy_status(name: str):
    """Get status of a specific strategy."""
    lc = _get_lifecycle()
    status = lc.get_status(name)
    if not status:
        raise HTTPException(status_code=404, detail=f"Strategy '{name}' not found")
    return status


@router.post("/{name}/start")
async def start_strategy(name: str):
    """Start a registered strategy."""
    lc = _get_lifecycle()
    success = lc.start(name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Could not start strategy '{name}'")
    return {"status": "started", "name": name}


@router.post("/{name}/stop")
async def stop_strategy(name: str):
    """Stop a running strategy."""
    lc = _get_lifecycle()
    success = lc.stop(name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Could not stop strategy '{name}'")
    return {"status": "stopped", "name": name}


@router.post("/{name}/pause")
async def pause_strategy(name: str):
    """Pause a running strategy."""
    lc = _get_lifecycle()
    success = lc.pause(name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Could not pause strategy '{name}'")
    return {"status": "paused", "name": name}


@router.post("/{name}/resume")
async def resume_strategy(name: str):
    """Resume a paused strategy."""
    lc = _get_lifecycle()
    success = lc.resume(name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Could not resume strategy '{name}'")
    return {"status": "resumed", "name": name}
