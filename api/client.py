import requests
from typing import Dict, Any, Optional
from utils.timezone import MarketTime

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
        
        # 한국 시간 헤더 추가 (API 서버 시간 동기화용)
        headers["X-Request-Time"] = MarketTime.format_korea_now()
        headers["X-Timezone"] = "Asia/Seoul"

        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        else:
            response = requests.post(url, headers=headers, params=params, json=data, timeout=10)
        
        response.raise_for_status()
        result = response.json()
        
        # 응답에 시간 정보 추가
        result["_request_meta"] = {
            "korea_time": MarketTime.format_korea_now(),
            "is_summer_time": MarketTime.is_summer_time()
        }
        return result

    def get(self, endpoint: str, tr_id: str = "", params: Optional[Dict] = None) -> Dict[str, Any]:
        return self.request("GET", endpoint, tr_id=tr_id, params=params)

    def post(self, endpoint: str, tr_id: str = "", params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        return self.request("POST", endpoint, tr_id=tr_id, params=params, data=data)
