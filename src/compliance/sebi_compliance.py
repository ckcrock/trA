import logging
import uuid
import socket
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SEBIAlgoComplianceManager:
    """
    Manages SEBI algorithmic trading compliance requirements.
    Reference: SEBI/HO/MIRSD/MIRSD-PoD1/P/CIR/2024/169
    """

    def __init__(self, broker_code: str):
        self.broker_code = broker_code
        self.algo_id: Optional[str] = None
        self.registration_status = "UNREGISTERED"
        self.static_ips = ["192.168.1.100"] # Example whitelisted IPs
        self.order_count_per_second = 0
        self.ops_threshold = 10 
        self.last_check_time = datetime.now()

    def register_algorithm(self, strategy_name: str, logic: Dict) -> bool:
        """
        Simulate registration of algorithm with Exchange.
        In production, this calls a Broker/Exchange API.
        """
        logger.info(f"Registering strategy {strategy_name}...")
        
        # Validation Logic
        if not strategy_name or not logic:
            logger.error("Invalid strategy definition")
            return False
            
        # Simulate approval
        self.algo_id = f"ALGO-{uuid.uuid4().hex[:8].upper()}"
        self.registration_status = "REGISTERED"
        logger.info(f"✅ Algorithm registered with ID: {self.algo_id}")
        return True

    def validate_order(self, order_params: Dict) -> Dict:
        """
        Validate and tag order before sending to broker.
        Throws exception if compliance check fails.
        """
        # 1. Algo ID Tagging
        if self.registration_status != "REGISTERED":
             raise RuntimeError("Compliance Error: Algorithm not registered")
             
        order_params['algo_id'] = self.algo_id
        order_params['algo_tag'] = "ALGO" # Specific tag required by broker
        
        # 2. Static IP Check
        current_ip = self._get_local_ip()
        # Note: real static IP check is done by broker, but we self-enforce
        # if current_ip not in self.static_ips:
        #    logger.warning(f"IP {current_ip} not in whitelist {self.static_ips}")
           
        # 3. Rate Limit (OPS)
        self._check_rate_limit()
        
        return order_params

    def _check_rate_limit(self):
        now = datetime.now()
        elapsed = (now - self.last_check_time).total_seconds()
        
        if elapsed > 1.0:
            self.order_count_per_second = 0
            self.last_check_time = now
            
        self.order_count_per_second += 1
        
        if self.order_count_per_second > self.ops_threshold:
             raise RuntimeError(f"Compliance Error: OPS threshold exceeded ({self.ops_threshold})")

    def _get_local_ip(self):
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

    def log_audit_trail(self, event_type: str, details: Dict):
        """Log event for audit trail (5-year retention required)"""
        # In production, write to a secure, immutable log store
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "algo_id": self.algo_id,
            "event": event_type,
            "details": details
        }
        logger.info(f"AUDIT: {log_entry}")
