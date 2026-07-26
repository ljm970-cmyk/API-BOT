import requests
from typing import Dict, Any, Optional

class KiwoomAPIError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

class KiwoomClient:
    def __init__(self, app_key: str, app_secret: str, base_url: str, account_no: str, mock: bool = False):
        from .auth import KiwoomAuth
        self.auth = KiwoomAuth(app_key, app_secret, base_url)
        self.base_url = base_url.rstrip('/')
        self.account_no = account_no
        self.mock = mock

    def request(self, method: str, endpoint: str, tr_id: str = "", params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        headers = self.auth.get_auth_header()
        headers["tr_id"] = tr_id
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        else:
            response = requests.post(url, headers=headers, params=params, json=data, timeout=10)
        
        response.raise_for_status()
        return response.json()

    def get(self, endpoint: str, tr_id: str = "", params: Optional[Dict] = None) -> Dict[str, Any]:
        return self.request("GET", endpoint, tr_id=tr_id, params=params)

    def post(self, endpoint: str, tr_id: str = "", params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        return self.request("POST", endpoint, tr_id=tr_id, params=params, data=data)
