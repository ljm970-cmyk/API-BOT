import base64
import requests
import time
from typing import Optional, Dict
from utils.logger import setup_logger

logger = setup_logger()

class KiwoomAuth:
    def __init__(self, app_key: str, app_secret: str, base_url: str = "https://api.kiwoom.com"):
        self.app_key = app_key.strip()
        self.app_secret = app_secret.strip()
        self.base_url = base_url.rstrip('/')
        self._access_token: Optional[str] = None
        self._token_expires: float = 0
        self.get_token()

    def _encode_credentials(self) -> str:
        credentials = f"{self.app_key}:{self.app_secret}"
        return base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

    def get_token(self) -> str:
        now = time.time()
        if self._access_token and now < (self._token_expires - 300):
            return self._access_token
        self._refresh_token()
        return self._access_token

    def _refresh_token(self):
        url = f"{self.base_url}/oauth2/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {self._encode_credentials()}"
        }
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecretkey": self.app_secret
        }
        response = requests.post(url, data=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        self._access_token = data.get("access_token")
        expires_in = int(data.get("expires_in", 86400))
        self._token_expires = time.time() + expires_in

    def get_auth_header(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.get_token()}",
            "Content-Type": "application/json; charset=utf-8",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "",
            "custtype": "P"
        }
