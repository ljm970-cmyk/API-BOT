from datetime import datetime, timedelta
import pytz
from enum import Enum
from typing import Tuple, Optional

class MarketTime:
    """
    미국 증시 시간 ↔ 한국 시간 변환
    
    미국 동부 시간 (ET):
    - 프리마켓: 04:00 ~ 09:30
    - 정규장:   09:30 ~ 16:00
    - 애프터장: 16:00 ~ 20:00
    
    한국 시간 (KST, 서머타임/비서머타임):
    - 서머타임 (3월 2일~11월 첫째주 일요일): ET + 13시간
    - 비서머타임 (나머지): ET + 14시간
    """
    
    EASTERN = 'US/Eastern'
    KOREA = 'Asia/Seoul'
    
    # 한국 시간 기준 영업 시간 [1]
    # 프리장 시작: 오후 5시 (서머타임) / 6시 (비서머타임)
    # 본장 마감: 새벽 5시 (서머타임) / 6시 (비서머타임)
    # 애프터장 마감: 새벽 9시 (서머타임) / 10시 (비서머타임)
    
    @classmethod
    def get_korea_time(cls) -> datetime:
        """현재 한국 시간"""
        kst = pytz.timezone(cls.KOREA)
        return datetime.now(kst)
    
    @classmethod
    def is_summer_time(cls, date: Optional[datetime] = None) -> bool:
        """
        해당 날짜가 서머타임 기간인지 여부
        
        서머타임: 3월 둘째주 일요일 02:00 시작
                11월 첫째주 일요일 02:00 종료
        """
        if date is None:
            date = cls.get_korea_time()
        
        et = pytz.timezone(cls.EASTERN)
        et_date = date.astimezone(et)
        
        # ET의 서머타임 여부 확인
        return bool(et_date.dst())

    @classmethod
    def get_market_hours_kst(cls, date: Optional[datetime] = None) -> dict:
        """
        해당 날짜의 미국증시 시간표 (한국 시간)
        """
        is_summer = cls.is_summer_time(date)
        
        # 오프셋
        summer_start = 17  # 오후 5시
        winter_start = 18  # 오후 6시
        
        kst_offset = summer_start if is_summer else winter_start
        
        result = {
            "is_summer_time": is_summer,
            "kst_premarket_start": kst_offset,       # 프리장 시작 (오후)
            "kst_regular_start": kst_offset + 9,     # 본장 시작 (오전...이어서 다음날)
            "kst_regular_end": kst_offset + 14,        # 본장 마감 (다음날 새벽)
            "kst_aftermarket_end": kst_offset + 16,    # 애프터장 마감
        }
        
        # 실제 시간 문자열 생성
        base_date = (cls.get_korea_time() + timedelta(days=1)).date() if cls.get_korea_time().hour >= 12 else cls.get_korea_time().date()
        
        result["schedule"] = {
            f"프리장 시작": f"{kst_offset}:00",
            f"본장 시작": f"다음날 ({kst_offset + 9})%24:00",
            f"지정가매도 걸기 추천 시간": f"{kst_offset}:00",
            f"본장 마감": f"다음날 {(kst_offset + 14) % 24}:00",
            f"애프터장 마감": f"다음날 {(kst_offset + 16) % 24}:00",
        }
        
        return result

    @classmethod
    def get_limit_order_deadline_kst(cls) -> Tuple[int, str]:
        """
        지정가매도 걸기 마감 추천 시간 (한국 시간)
        
        [1] 프리장이 시작하는 저녁 5시(서머타임) or 6시(비서머타임)
        """
        is_summer = cls.is_summer_time()
        hour = 17 if is_summer else 18
        label = "오후 5시" if is_summer else "오후 6시"
        return (hour, label)

    @classmethod
    def format_korea_now(cls) -> str:
        """현재 한국 시간 문자열"""
        return cls.get_korea_time().strftime("%Y-%m-%d %H:%M:%S KST")

    @classmethod
    def can_place_limit_order_now(cls) -> bool:
        """
        지정가 매도 주문 가능 여부
        
        프리장 ~ 애프터장까지 효력 유지되므로,
        프리장 시작 직전(저녁 5/6시)에 걸어두면 다음날 애프터까지 유효
        """
        now = cls.get_korea_time()
        hour = now.hour
        
        # 오후 4시30분 ~ 저녁 8시 사이에 걸 수 있음
        # (실제로는 24시간 가능, 하지만 효율적으로 maximize 하려면)
        return True  # 애프터까지 효력 유지하므로 언제든 가능

    @classmethod
    def next_loc_expiry_kst(cls) -> datetime:
        """
        내일 LOC 주문 만료 시간 (다음날 미국 장 마감)
        """
        now = cls.get_korea_time()
        tomorrow = now + timedelta(days=1)
        
        # LOC는 당일 장 마감 시까지 유효
        # 다음날 새벽 5시(서머타임) or 6시(비서머타임)
        is_summer = cls.is_summer_time(tomorrow)
        hour = 5 if is_summer else 6
        
        expiry = tomorrow.replace(hour=hour, minute=0, second=0)
        return expiry


class OrderTimeFormatter:
    """주문 시간 포맷터 (텔레그램/로그용)"""
    
    @classmethod
    def order_time_info(cls) -> str:
        """현재 시간 정보 + 주문 가능 시간 요약"""
        kst = MarketTime.get_korea_time()
        is_summer = MarketTime.is_summer_time()
        
        summer_text = "서머타임 적용중" if is_summer else "비서머타임"
        limit_hour = 17 if is_summer else 18
        limit_label = f"오후 {limit_hour % 12}:00"
        if limit_hour == 17:
            limit_label = "저녁 5시"
        else:
            limit_label = "저녁 6시"
        
        return (
            f"현재: {kst.strftime('%Y-%m-%d %H:%M')} KST\n"
            f"뉴욕: {is_summer_text}\n"
            f"지정가매도 걸기: {limit_label} (프리장 시작 전)\n"
            f"지정가매도 효력: 프리장 → 본장 → 애프터장 (다음날 새벽까지)"
        )
