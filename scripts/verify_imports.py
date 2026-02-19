"""
Comprehensive Import Verification Script.
Checks availability of all key dependencies:
1. Angel One SmartAPI
2. Nautilus Trader (Optional)
3. Standard Libraries (pandas, numpy, etc.)
4. Project Internal Modules
"""

import sys
import importlib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ImportVerifier")

def check_import(module_name: str, package_name: str = None) -> bool:
    """Try to import a module and report status."""
    pkg = package_name or module_name
    try:
        importlib.import_module(module_name)
        logger.info(f"✅ [OK] {pkg}")
        return True
    except ImportError as e:
        logger.warning(f"❌ [MISSING] {pkg}: {e}")
        return False
    except Exception as e:
        logger.error(f"⚠️ [ERROR] {pkg}: {e}")
        return False

def verify_all():
    logger.info("="*40)
    logger.info(" 🔍 Verifying Project Dependencies")
    logger.info("="*40)

    # 1. Angel One SDK
    logger.info("\n--- Angel One SDK ---")
    check_import("SmartApi", "smartapi-python")
    check_import("SmartApi.smartWebSocketV2", "smartapi-websocket")
    check_import("pyotp", "pyotp")

    # 2. Nautilus Trader (Target Integration)
    logger.info("\n--- Nautilus Trader (Optional) ---")
    nautilus_ok = check_import("nautilus_trader", "nautilus_trader")
    if nautilus_ok:
        check_import("nautilus_trader.model.data", "nautilus_trader.model")
        check_import("nautilus_trader.trading.node", "nautilus_trader.node")
    else:
        logger.info("ℹ️ Nautilus Trader is optional. Adapters will be disabled.")

    # 3. Core Data Science & API
    logger.info("\n--- Core Libraries ---")
    check_import("pandas", "pandas")
    check_import("numpy", "numpy")
    check_import("fastapi", "fastapi")
    check_import("uvicorn", "uvicorn")
    check_import("pydantic", "pydantic")
    check_import("yaml", "PyYAML")
    check_import("redis", "redis")
    check_import("psycopg2", "psycopg2-binary")
    
    # 4. Project Internals
    logger.info("\n--- Project Modules ---")
    sys.path.append(".") # Ensure CWD is in path
    
    modules = [
        "src.adapters.angel.auth",
        "src.adapters.angel.data_client",
        "src.adapters.angel.execution_client",
        "src.adapters.nautilus", # Should not crash even if Nautilus missing
        "src.engine.node",
        "src.strategies.ema_crossover",
        "src.api.main"
    ]
    
    success_count = 0
    for mod in modules:
        if check_import(mod):
            success_count += 1
            
    logger.info("\n" + "="*40)
    logger.info(f"Summary: {success_count}/{len(modules)} Internal Modules Loaded")
    logger.info("="*40)

if __name__ == "__main__":
    verify_all()
