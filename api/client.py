import requests
from typing import Dict, Any, Optional

class KiwoomClient:
    """
    키움증권 REST API 통합 클라이언트
    
    국내 + 해외주식 모두 지원
    """
    
    def __init__(self, app_key: str, app_secret: str, base_url: str, 
                 account_no: str, mock: bool = False):
        from .auth import KiwoomAuth
        from .kiwoom_overseas import KiwoomOverseasAPI
        
        self.auth = KiwoomAuth(app_key, app_secret, base_url)
        self.base_url = base_url.rstrip('/')
        self.account_no = account_no
        self.mock = mock
        
        # 해외주식 API 연동
        self.overseas = KiwoomOverseasAPI(self.auth, account_no, mock)
        
        # 국내/해외 플래그
        self.is_overseas = False

    def switch_to_overseas(self):
        """해외주식 모드로 전환"""
        self.is_overseas = True
        self.overseas.is_domestic = False
    
    def switch_to_domestic(self):
        """국내주식 모드로 전환"""
        self.is_overseas = False

    def get_price(self, stock_code: str, market: str = "NAS") -> Dict[str, Any]:
        """
        현재가 조회 (자동 분기)
        
        해외주식: TQQQ, SOXL (NAS)
        국내주식: 6자리 종목코드
        """
        if self.is_overseas or stock_code.isalpha():
            # 해외주식 (영문 종목코드: TQQQ, SOXL)
            return self.overseas.get_price(stock_code, market)
        else:
            # 국내주식
            return self._get_domestic_price(stock_code)

    def _get_domestic_price(self, stock_code: str) -> Dict[str, Any]:
        """국내주식 현재가 (기존 코드)"""
        # ... 기존 국내주식 API 호출 ...
        pass

    def order(self, stock_code: str, side: str, quantity: int,
              price: float = 0, order_type: str = "LOC",
              market: str = "NAS") -> Dict[str, Any]:
        """
        주문 실행 (자동 분기)
        """
        if self.is_overseas or stock_code.isalpha():
            return self.overseas.order(
                stock_code=stock_code,
                side=side,
                quantity=quantity,
                price=price,
                order_type=order_type,
                market=market
            )
        else:
            return self._order_domestic(stock_code, side, quantity, price, order_type)

    def _order_domestic(self, stock_code: str, side: str, quantity: int,
                        price: float, order_type: str) -> Dict[str, Any]:
        """국내주식 주문 (기존 코드)"""
        # ... 기존 국내주식 주문 ...
        pass

    def get_balance(self) -> Dict[str, Any]:
        """잔고 조회 (자동 분기)"""
        if self.is_overseas:
            return self.overseas.get_balance()
        else:
            # 국내 잔고
            pass

    # ========== 편의 메서드 ==========
    
    def get_tqqq_price(self) -> float:
        """TQQQ 현재가 편의 메서드"""
        result = self.overseas.get_price("TQQQ", "NAS")
        return float(result.get("output", {}).get("last", 0))
    
    def get_soxl_price(self) -> float:
        """SOXL 현재가 편의 메서드"""
        result = self.overseas.get_price("SOXL", "NAS")
        return float(result.get("output", {}).get("last", 0))
    
    def buy_tqqq(self, quantity: int, price: float = 0, order_type: str = "LOC"):
        """TQQQ 매수 편의 메서드"""
        return self.overseas.order("TQQQ", "BUY", quantity, price, order_type, "NAS")
    
    def sell_tqqq(self, quantity: int, price: float = 0, order_type: str = "LOC"):
        """TQQQ 매도 편의 메서드"""
        return self.overseas.order("TQQQ", "SELL", quantity, price, order_type, "NAS")
    
    def buy_soxl(self, quantity: int, price: float = 0, order_type: str = "LOC"):
        """SOXL 매수 편의 메서드"""
        return self.overseas.order("SOXL", "BUY", quantity, price, order_type, "NAS")
    
    def sell_soxl(self, quantity: int, price: float = 0, order_type: str = "LOC"):
        """SOXL 매도 편의 메서드"""
        return self.overseas.order("SOXL", "SELL", quantity, price, order_type, "NAS")
