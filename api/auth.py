import base64
import requests
import time
from typing import Optional, Dict
from utils.logger import setup_logger

logger = setup_logger()


class KiwoomAuth:
    """
    키움증권 OAuth 2.0 인증 관리
    - client_credentials 방식
    - 토큰 만료 시 자동 재발급
    """

    def __init__(self, app_key: str, app_secret: str, base_url: str = "https://api.kiwoom.com"):
        self.app_key = app_key.strip()
        self.app_secret = app_secret.strip()
        self.base_url = base_url.rstrip('/')
        self._access_token: Optional[str] = None
        self._token_expires: float = 0  # 유닉스 타임스탬프
        # 초기 토큰 발급
        self.get_token()

    def _encode_credentials(self) -> str:
        """Basic Auth용 Base64 인코딩"""
        credentials = f"{self.app_key}:{self.app_secret}"
        encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        return encoded

    def get_token(self) -> str:
        """유효한 토큰 반환 (만료 시 자동 재발급)"""
        now = time.time()
        # 토큰 유효 여부 확인 (만료 5분 전 재발급)
        if self._access_token and now < (self._token_expires - 300):
            return self._access_token
        
        # 토큰 재발급
        logger.info("Access Token 재발급 요구")
        self._refresh_token()
        return self._access_token

    def _refresh_token(self):
        """토큰 발급/재발급"""
        url = f"{self.base_url}/oauth2/token"
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {self._encode_credentials()}"
        }
        
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecretkey": self.app_secret  # 실제 필드명 확인 필요
        }

        try:
            response = requests.post(url, data=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self._access_token = data.get("access_token")
            expires_in = int(data.get("expires_in", 86400))
            self._token_expires = time.time() + expires_in
            
            # 토큰 타입 확인
            token_type = data.get("token_type", "Bearer")
            logger.info(f"토큰 발급 완료: {token_type}, 만료 {expires_in}초")

        except requests.exceptions.HTTPError as e:
            error_data = e.response.json() if e.response.content else {}
            logger.error(f"토큰 발급 실패 HTTP {e.response.status_code}: {error_data}")
            raise
        except Exception as e:
            logger.error(f"토큰 발급 중 예외: {e}")
            raise

    def get_auth_header(self) -> Dict[str, str]:
        """API 호출용 인증 헤더"""
        token = self.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

    def revoke_token(self):
        """토큰 폐기 (프로그램 종료 시 권장)"""
        if not self._access_token:
            return
        
        url = f"{self.base_url}/oauth2/revoke"
        
        headers = {
            "Authorization": f"Basic {self._encode_credentials()}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        payload = {
            "token": self._access_token
        }

        try:
            response = requests.post(url, data=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                logger.info("토큰 폐기 완료")
            self._access_token = None
            self._token_expires = 0
        except Exception as e:
            logger.warning(f"토큰 폐기 중 오류: {e}")
