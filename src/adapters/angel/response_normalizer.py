from __future__ import annotations

from typing import Any, Dict, Optional


def normalize_smartapi_response(response: Any) -> Dict[str, Any]:
    """
    Normalize SmartAPI responses into a stable shape.

    Supported raw forms:
    - {"status": True/False, "message": "...", "data": ...}
    - {"success": True/False, "message": "...", "data": ...}
    - {"error": "..."} / {"errorcode": "...", "message": "..."}
    - Plain strings (often order id for placeOrder)
    - None
    """
    normalized = {
        "ok": False,
        "message": "",
        "error_code": "",
        "data": None,
        "raw": response,
    }

    if response is None:
        normalized["message"] = "No response"
        return normalized

    if isinstance(response, str):
        normalized["ok"] = True
        normalized["data"] = response
        return normalized

    if isinstance(response, dict):
        status_value = response.get("status")
        success_value = response.get("success")
        has_success_flag = isinstance(status_value, bool) or isinstance(success_value, bool)
        ok = bool(status_value) if isinstance(status_value, bool) else bool(success_value)

        # Some APIs may not provide explicit status but still return usable data.
        if not has_success_flag and "data" in response and "error" not in response:
            ok = True

        normalized["ok"] = ok
        normalized["message"] = str(response.get("message") or response.get("error") or "")
        normalized["error_code"] = str(response.get("errorcode") or response.get("code") or "")
        normalized["data"] = response.get("data")
        return normalized

    normalized["message"] = f"Unsupported response type: {type(response).__name__}"
    return normalized


def extract_order_id(response: Any) -> Optional[str]:
    """
    Extract order id from known SmartAPI placeOrder variants.
    """
    if isinstance(response, str) and response.strip():
        return response.strip()

    if not isinstance(response, dict):
        return None

    data = response.get("data") or {}
    for key in ("orderid", "orderId", "order_id"):
        value = data.get(key)
        if value:
            return str(value)

    for key in ("orderid", "orderId", "order_id"):
        value = response.get(key)
        if value:
            return str(value)

    return None
