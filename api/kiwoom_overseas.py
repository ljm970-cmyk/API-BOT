import requests
from typing import Dict, Any, Optional
from dataclasses import dataclass
from api.auth import KiwoomAuth
from utils.logger import setup_logger

logger = setup_logger()


@dataclass
class OverseasPrice:
    """해외주식 현재가 응답 파싱"""
    stock_code: str
    current_price: float
    change: float
    change_rate: float
    volume: int
    
    @classmethod
    def from_response(cls, data: dict) -> "OverseasPrice":
        output = data.get("output", {})
        return cls(
            stock_code=output.get("symbol", ""),
            current_price=float(output.get("last", 0)),
            change=float(output.get("diff", 0)),
            change_rate=float(output.get("rate", 0)),
            volume=int(output.get("tvol", 0))
        )


class KiwoomOverseasAPI:
    """
    키움증권 REST API - 해외주식 (미국)
    
    엔드포인트: https://api.kiwoom.com
    해외주식 거래 API 별도 경로
    """
    
    def __init__(self, auth: KiwoomAuth, account_no: str, mock: bool = False):
        self.auth = auth
        self.base_url = "https://api.kiwoom.com"
        self.account_no = account_no
        self.mock = mock
        self.is_domestic = False  # 해외주식 플래그
        
        # 해외주식 계좌번호 구성
        # 일반: 8자리계좌 + "00" (미국)
        self.account_prefix = account_no[:8] if len(account_no) >= 8 else account_no
        self.account_product = "00"  # 해외주식 상품코드 (미국)

    def _get_headers(self, tr_id: str = "") -> Dict[str, str]:
        """해외주식 호출용 헤더"""
        headers = self.auth.get_auth_header()
        headers.update({
            "Content-Type": "application/json; charset=utf-8",
            "tr_id": tr_id,
            "custtype": "P",  # 개인
            "is_overseas": "Y"  # 해외주식 플래그 (있는 경우)
        })
        return headers

    def get_price(self, stock_code: str, market: str = "NAS") -> Dict[str, Any]:
        """
        해외주식 현재가 조회
        
        market: NAS (나스닥), NYS (뉴욕), AMX (AMEX)
        
        실제 TR_ID 확인 필요:
        - 실전: VSIn001C (확인 필요)
        - 모의: VSIn001C? 또는 별도
        """
        # 키움 해외주식 현재가 TR
        tr_id = "VSIn001C"  # 실전/모의 구분 확인 필요
        
        url = f"{self.base_url}/api/v1/price/overseas"
        
        params = {
            "SYMB": stock_code,      # 종목코드
            "EXCD": market,          # 거래소
            "CUST_ID": "",           # 고객ID (필요시)
        }
        
        try:
            response = requests.get(
                url, 
                headers=self._get_headers(tr_id),
                params=params,
                timeout=10
            )
            
            result = self._parse_response(response)
            logger.info(f"해외주식 현재가: {stock_code} ${result.get('output', {}).get('last', 0)}")
            return result
            
        except Exception as e:
            logger.error(f"해외주식 현재가 조회 실패: {e}")
            raise

    def order(self, stock_code: str, side: str, quantity: int,
              price: float = 0, order_type: str = "LOC",
              market: str = "NAS") -> Dict[str, Any]:
        """
        해외주식 주문
        
        side: "BUY" or "SELL"
        order_type: "LOC", "MOC", "LIMIT"
        
        해외주식 주문 TR:
        - 실전 매수: VTTS1008U? (실제 키움 문서 확인 필요)
        - 실전 매도: VTTS1009U?
        - 모의 매수: VTTT1008U?
        - 모의 매도: VTTT1009U?
        """
        # 모의/실전 + 매수/매도 구분
        if self.mock:
            tr_id = "VTTT1002U" if side == "BUY" else "VTTT1001U"  # 모의, 실제 번호는 문서 확인
        else:
            tr_id = "TTTT1002U" if side == "BUY" else "TTTT1001U"
        
        # 해외주식 주문은 별도 경로 사용 가능
        url = f"{self.base_url}/api/v1/order/overseas"
        
        # 주문구분 변환
        # LOC: "00"
        # MOC: "01" (장마감)
        # 시장가: "02"
        order_div = {
            "LOC": "00",
            "MOC": "01",
            "MARKET": "02",
            "LIMIT": "03"
        }.get(order_type, "00")
        
        body = {
            "CANO": self.account_prefix,
            "ACNT_PRDT_CD": self.account_product,
            "OVRS_EXCG_CD": market,           # 해외거래소
            "PDNO": stock_code,                # 종목코드
            "ORD_DVSN": order_div,            # 주문구분
            "ORD_QTY": str(quantity),         # 주문수량
            "OVRS_ORD_UNPR": str(price) if price > 0 else "0",  # 해외주문단가
            "SLL_BUY_DVSN_CD": "01" if side == "BUY" else "02",  # 01매수 02매도
            "ORD_SVR_DVSn_CD": "0",           # 주문서버구분 (미국)
            "ORD_OBJT_CCLD_DTTM": "",         # 주문목적체결일시 (LOC용)
        }
        
        try:
            headers = self._get_headers(tr_id)
            # POST 요청
            response = requests.post(
                url,
                headers=headers,
                json=body,
                timeout=10
            )
            
            result = self._parse_response(response)
            logger.info(f"해외주식 주문: {stock_code} {side} {quantity}주 @ ${price}")
            return result
            
        except Exception as e:
            logger.error(f"해외주식 주문 실패: {e}")
            raise

    def get_balance(self) -> Dict[str, Any]:
        """
        해외주식 잔고 조회
        
        TR: 해외주식 잔고 조회용
        """
        tr_id = "VTTS3012R" if self.mock else "TTTS3012R"
        
        url = f"{self.base_url}/api/v1/account/overseas-balance"
        
        params = {
            "CANO": self.account_prefix,
            "ACNT_PRDT_CD": self.account_product,
            "WCRC_FRCR_DVSN_CD": "02",   # 외화구분: 02 (USD)
            "NATN_CD": "840",            # 국가코드: 미국
            "TRAD_DVSND_CD": "01",       # 매매구분?
            "CRCY_CD": "USD",            # 통화코드
        }
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(tr_id),
                params=params,
                timeout=10
            )
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"해외주식 잔고 조회 실패: {e}")
            raise

    def get_order_history(self, start_date: str = "", end_date: str = "") -> Dict[str, Any]:
        """
        해외주식 주문 내역 조회
        """
        tr_id = "VTTS1007R" if self.mock else "TTTS1007R"
        
        url = f"{self.base_url}/api/v1/orders/overseas"
        
        params = {
            "CANO": self.account_prefix,
            "ACNT_PRDT_CD": self.account_product,
            "INQR_STRT_DT": start_date,
            "INQR_END_DT": end_date,
            "SLL_BUY_DVSN_CD": "0",   # 0: 전체 1: 매도 2: 매수
        }
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(tr_id),
                params=params,
                timeout=10
            )
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"해외주식 주문내역 조회 실패: {e}")
            raise

    def _parse_response(self, response: requests.Response) -> Dict[str, Any]:
        """공통 응답 파싱"""
        response.raise_for_status()
        data = response.json()
        
        # 키움 API 공통 응답
        rt_cd = data.get("rt_cd", "1")
        if rt_cd != "0":
            msg = data.get("msg1", "Unknown error")
            raise Exception(f"API Error: {msg} (rt_cd={rt_cd})")
        
        return data
