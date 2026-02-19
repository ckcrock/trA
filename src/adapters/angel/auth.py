import logging
import pyotp
import threading
from SmartApi import SmartConnect
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class AngelAuthManager:
    """
    Manages authentication with Angel One SmartAPI.
    Handles login, session maintenance, TOTP generation, and token management.
    
    Reference: docs/angle/angel_one_complete_integration.py (AngelOneAuth)
    """

    def __init__(
        self, 
        api_key: str, 
        client_code: str, 
        mpin: str, 
        totp_secret: str,
        hist_api_key: str = None
    ):
        """
        Args:
            api_key: Angel One API key
            client_code: Your Angel One client code (e.g. "PPSU15866")
            mpin: Your 4-digit MPIN (NOT old password)
            totp_secret: TOTP secret for 2FA
            hist_api_key: Separate API key for historical data (optional)
        """
        self.api_key = api_key
        self.hist_api_key = hist_api_key
        self.client_code = client_code
        self.mpin = mpin
        self.totp_secret = totp_secret
        
        # Initialize SmartConnect clients
        self.smart_api = SmartConnect(api_key=self.api_key)
        self.hist_smart_api = SmartConnect(api_key=self.hist_api_key) if self.hist_api_key else None
        
        # Session data
        self.session_data: Optional[Dict[str, Any]] = None
        self.last_login_time: Optional[datetime] = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        self.session_expiry: Optional[datetime] = None
        self.profile_data: Optional[Dict] = None
        
        # Auto-refresh
        self.auto_refresh_enabled = True
        self.refresh_timer: Optional[threading.Timer] = None
        
        logger.info("✅ Angel One Auth Manager initialized")

    def _generate_totp(self) -> str:
        """Generate time-based OTP."""
        try:
            totp = pyotp.TOTP(self.totp_secret).now()
            return totp
        except Exception as e:
            logger.error(f"❌ Failed to generate TOTP: {e}")
            raise

    def login(self) -> bool:
        """
        Perform login to Angel One using MPIN + TOTP.
        Returns True if successful, False otherwise.
        """
        try:
            logger.info("🔐 Logging in to Angel One...")
            totp = self._generate_totp()
            
            # generateSession expects (clientCode, password/mpin, totp)
            response = self.smart_api.generateSession(
                clientCode=self.client_code,
                password=self.mpin,
                totp=totp
            )
            
            if not response or not response.get('status'):
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                logger.error(f"❌ Login failed: {error_msg}")
                return False
            
            # Extract tokens
            data = response.get('data', {})
            self.session_data = data
            self.access_token = data.get('jwtToken')
            self.refresh_token = data.get('refreshToken')
            self.feed_token = self.smart_api.getfeedToken()
            self.last_login_time = datetime.now()
            self.session_expiry = datetime.now() + timedelta(hours=6)
            
            # Set session expiry hook
            self.smart_api.setSessionExpiryHook(self.refresh_session)
            
            # Get profile
            self.profile_data = self.get_profile()
            
            # If historical client exists, authenticate it too
            if self.hist_smart_api:
                try:
                    hist_totp = self._generate_totp()
                    hist_response = self.hist_smart_api.generateSession(
                        clientCode=self.client_code,
                        password=self.mpin,
                        totp=hist_totp
                    )
                    if hist_response and hist_response.get('status'):
                        logger.info("✅ Historical API client authenticated")
                    else:
                        # Fallback: share tokens
                        logger.warning("⚠️ Hist client login failed, sharing tokens from main client")
                        self.hist_smart_api.setAccessToken(self.access_token)
                except Exception as he:
                    logger.warning(f"⚠️ Hist client auth fallback: {he}")
                    self.hist_smart_api.setAccessToken(self.access_token)
            
            # Start auto-refresh timer
            if self.auto_refresh_enabled:
                self._schedule_auto_refresh()
            
            logger.info(f"✅ Successfully logged in as {self.client_code}")
            logger.info(f"   Session expires: {self.session_expiry.strftime('%Y-%m-%d %H:%M:%S')}")
            return True
                
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False

    def refresh_session(self) -> bool:
        """Refresh the session using the refresh token."""
        try:
            logger.info("🔄 Refreshing session...")
            
            if not self.refresh_token:
                logger.warning("No refresh token available. Re-logging in...")
                return self.login()
            
            response = self.smart_api.generateToken(self.refresh_token)
            
            if response and response.get('status'):
                data = response.get('data', {})
                self.access_token = data.get('jwtToken')
                self.feed_token = self.smart_api.getfeedToken()
                self.refresh_token = data.get('refreshToken', self.refresh_token)
                self.session_expiry = datetime.now() + timedelta(hours=6)
                
                # Update session_data
                if self.session_data:
                    self.session_data['jwtToken'] = self.access_token
                    self.session_data['feedToken'] = self.feed_token
                
                logger.info("✅ Session refreshed successfully")
                return True
            else:
                error_msg = response.get('message', 'Unknown') if response else 'No response'
                logger.error(f"❌ Session refresh failed: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Session refresh error: {e}")
            return False

    def logout(self) -> bool:
        """Logout from Angel One."""
        try:
            logger.info("🚪 Logging out...")
            response = self.smart_api.terminateSession(self.client_code)
            
            if response and response.get('status'):
                logger.info("✅ Logout successful")
                
                if self.refresh_timer:
                    self.refresh_timer.cancel()
                
                self.access_token = None
                self.refresh_token = None
                self.feed_token = None
                self.session_expiry = None
                self.session_data = None
                return True
            else:
                logger.error(f"❌ Logout failed: {response}")
                return False
        except Exception as e:
            logger.error(f"❌ Logout exception: {e}")
            return False

    def is_session_valid(self) -> bool:
        """Check if current session is valid and not expiring soon."""
        if not self.access_token:
            return False
        
        if self.session_expiry:
            time_remaining = (self.session_expiry - datetime.now()).total_seconds()
            if time_remaining < 1800:  # 30 minutes
                logger.warning("⚠️ Session expiring soon, need refresh")
                return False
        
        return True

    def ensure_authenticated(self) -> bool:
        """
        Ensure valid authentication. Refresh or re-login if needed.
        Call this before any API operation.
        """
        if self.is_session_valid():
            return True
        
        # Try refresh first
        if self.refresh_token:
            if self.refresh_session():
                return True
        
        # Re-login if refresh failed
        logger.info("🔄 Re-authenticating...")
        if not self.login():
            raise RuntimeError("Failed to authenticate with Angel One.")
        return True

    def get_profile(self) -> Optional[Dict]:
        """Get user profile."""
        try:
            response = self.smart_api.getProfile(self.refresh_token)
            if response and response.get('status'):
                return response.get('data')
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching profile: {e}")
            return None

    def get_smart_api_client(self) -> SmartConnect:
        """Return the authenticated SmartConnect instance."""
        if not self.access_token:
            raise RuntimeError("Client not authenticated. Call login() first.")
        return self.smart_api

    def get_hist_client(self) -> SmartConnect:
        """Return the SmartConnect instance for historical data."""
        if not self.access_token:
            raise RuntimeError("Client not authenticated. Call login() first.")
        return self.hist_smart_api if self.hist_smart_api else self.smart_api

    def _schedule_auto_refresh(self):
        """Schedule automatic session refresh every 5 hours."""
        refresh_interval = 5 * 60 * 60  # 5 hours

        def refresh_task():
            if self.auto_refresh_enabled:
                self.refresh_session()
                self._schedule_auto_refresh()

        if self.refresh_timer:
            self.refresh_timer.cancel()

        self.refresh_timer = threading.Timer(refresh_interval, refresh_task)
        self.refresh_timer.daemon = True
        self.refresh_timer.start()
        logger.info(f"⏰ Auto-refresh scheduled for {refresh_interval/3600} hours")
