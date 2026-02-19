from fastapi import APIRouter, Depends
from typing import Dict
from src.api.dependencies import get_execution_client
from src.adapters.angel.execution_client import AngelExecutionClient

router = APIRouter()

@router.get("/")
async def get_positions(client: AngelExecutionClient = Depends(get_execution_client)):
    return await client.get_positions()
