import requests
import json
from typing import Dict, Any, Optional
from utils.logger import setup_logger

logger = setup_logger()


class KiwoomAPIError(Exception):
    """키움 API 에러"""
    def __init__(self, code: str, message: str, response_data: Dict = None):
        self.code = code
        self.message = message
        self.response_data = response_data or {}
        super().__init__(f"[{code}] {message}")


class KiwoomClient:
    """키움증권 REST API 클라이언트"""

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        base_url: str,
        account_no: str,
        mock: bool = False
    ):
        from .auth import KiwoomAuth
        self.auth = KiwoomAuth(app_key, app_secret, base_url)
        self.base_url = base_url.rstrip('/')
        self.account_no = account_no
        self.mock = mock

    def _get_headers(self, tr_id: str = "") -> Dict[str, str]:
        """공통 헤더 생성"""
        headers = self.auth.get_auth_header()
        headers["custtype"] = "P"  # 개인
        
        if tr_id:
            headers["tr_id"] = tr_id
        
        # 모의투자구분
        if self.mock:
            headers["tr_cont"] = "N"  # 연속조회 여부
        
        return headers

    def _parse_response(self, response: requests.Response) -> Dict[str, Any]:
        """응답 파싱 및 에러 처리"""
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise KiwoomAPIError("E999", f"JSON 파싱 실패: {response.text[:200]}")

        # 키움 API 공통 응답 구조
        rt_cd = data.get("rt_cd", "1")
        msg_cd = data.get("msg_cd", "UNKNOWN")
        msg1 = data.get("msg1", "Unknown error")

        # 성공 (rt_cd: "0")
        if rt_cd == "0":
            return {
                "success": True,
                "code": msg_cd,
                "message": msg1,
                "data": data.get("output", data.get("output1", data.get("output2", {}))),
                "raw": data
            }

        # 실패
        raise KiwoomAPIError(msg_cd, msg1, data)

    def request(
        self,
        method: str,
        endpoint: str,
        tr_id: str = "",
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """HTTP 요청 공통 처리"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(tr_id)

        # 로깅 (민감 정보 제외)
        log_headers = {k: v for k, v in headers.items() if k.lower() not in ['authorization', 'appsecret']}
        logger.debug(f"[{method}] {endpoint} | tr_id={tr_id} | headers={log_headers}")

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            else:
                response = requests.post(
                    url,
                    headers=headers,
                    params=params,  # Query Param (주문시 필요)
                    json=data,      # Body
                    timeout=timeout
                )
            
            response.raise_for_status()  # HTTP 에러 체크
            return self._parse_response(response)

        except requests.exceptions.Timeout:
            raise KiwoomAPIError("E001", f"요청 시간 초과: {endpoint}")
        except requests.exceptions.ConnectionError:
            raise KiwoomAPIError("E002", f"연결 실패: {endpoint}")
        except KiwoomAPIError:
            raise
        except Exception as e:
            raise KiwoomAPIError("E999", f"요청 중 예외: {str(e)}")

    def get(self, endpoint: str, tr_id: str = "", params: Optional[Dict] = None) -> Dict[str, Any]:
        return self.request("GET", endpoint, tr_id=tr_id, params=params)

    def post(self, endpoint: str, tr_id: str = "", params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        return self.request("POST", endpoint, tr_id=tr_id, params=params, data=data)
