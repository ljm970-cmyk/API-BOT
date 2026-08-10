#!/usr/bin/env python3
"""
KST(한국 시간) 영구 고정 유틸리티
서버 TZ 변경, 재부팅, 여름/겨울 시기 전환에도 정확한 KST 보장
"""

import os
import time
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from dataclasses import dataclass

# ========== TZ 즉시 강제 ==========
os.environ['TZ'] = 'Asia/Seoul'
try:
    time.tzset()
except AttributeError:
    pass  # Windows는 tzset 없음

try:
    import pytz
    _PYTZ_AVAILABLE = True
except ImportError:
    _PYTZ_AVAILABLE = False
    print("WARNING: pytz 미설치. pip install pytz 권장.")


# ========== 전역 상수 ==========
KST_ZONE_NAME = 'Asia/Seoul'
UTC_ZONE_NAME = 'UTC'
KST_OFFSET_SECONDS = 9 * 3600  # +32400초


@dataclass
class TimeVerificationResult:
    """시간대 검증 결과"""
    ok: bool                        # KST 정상 여부
    kst_now_str: str                # KST 현재 시각
    utc_now_str: str                # UTC 현재 시각
    offset_hours: float             # UTC 대비 오프셋 (시간)
    server_tz_env: str              # 서버 TZ 환경변수
    calc_method: str                # 어떤 방법으로 계산했는지
    warning: Optional[str] = None  # 문제 있을 때 경고 메시지


class MarketTime:
    """
    한국 시간(KST) 관리 - 서버 TZ 무관하게 정확한 KST 계산
    """

    _kst_zone: Optional['pytz.timezone'] = None
    _utc_zone: Optional['pytz.timezone'] = None
    _use_pytz: bool = False

    @classmethod
    def _init_zones(cls):
        """존 객체 초기화 (지연 로딩)"""
        if cls._kst_zone is None and _PYTZ_AVAILABLE:
            cls._kst_zone = pytz.timezone(KST_ZONE_NAME)
            cls._utc_zone = pytz.timezone(UTC_ZONE_NAME)
            cls._use_pytz = True

    # ========== 핵심: KST 현재 시각 (믿을 수 있는 버전) ==========

    @classmethod
    def get_korea_time(cls) -> datetime:
        """
        현재 KST 시간 - 서버 TZ 설정과 무관
        
        방법: UTC 기준 → KST 변환 (가장 안정)
        서버가 UTC로 돌아가도 +9시간 보장
        """
        cls._init_zones()

        if cls._use_pytz:
            # 방법 1: pytz UTC 기준 변환 (권장)
            utc_now = datetime.now(cls._utc_zone)
            kst_now = utc_now.astimezone(cls._kst_zone)
            return kst_now.replace(tzinfo=None)  # offset 제거, 순수 datetime 리턴
        else:
            # 방법 2: pytz 없을 때 수동 계산
            utc_now = datetime.utcnow()
            # KST=UTC+9, DST 없음 (한국 1961년 이후 DST 폐지)
            kst_now = utc_now + timedelta(seconds=KST_OFFSET_SECONDS)
            return kst_now

    @classmethod
    def get_korea_now_str(cls, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        """KST 현재 시각 문자열"""
        return cls.get_korea_time().strftime(f"{fmt} KST")

    @classmethod
    def today_kst(cls, fmt: str = "%Y%m%d") -> str:
        """오늘 날짜 YYYYMMDD"""
        return cls.get_korea_time().strftime(fmt)

    # ========== 장 시간 계산 ==========

    @classmethod
    def is_summer_time(cls, date: Optional[datetime] = None) -> bool:
        """
        현재 뉴욕 서머타임 여부 (KST 기준 프리장 시간 판단용)
        
        서머타임: 3월 둘째주 일요일 ~ 11월 첫째주 일요일
        한국은 DST 없으므로 미국 DST만 체크
        """
        cls._init_zones()
        now = date or cls.get_korea_time()

        if cls._use_pytz:
            et_zone = pytz.timezone('US/Eastern')
            et_now = et_zone.localize(now.replace(tzinfo=None))
            return bool(et_now.dst())

        # pytz 없으면 근사 계산
        year = now.year
        # 3월 둘째주 일요일
        march = datetime(year, 3, 8)
        dst_start = march + timedelta(days=(6 - march.weekday()) % 7 + 7)
        # 11월 첫째주 일요일
        nov = datetime(year, 11, 1)
        dst_end = nov + timedelta(days=(6 - nov.weekday()) % 7)

        return dst_start <= now.replace(tzinfo=None) < dst_end

    @classmethod
    def get_limit_order_deadline_kst(cls) -> Tuple[int, str]:
        """
        지정가매도 권장 시간 (KST 기준)
        
        서머타임: 저녁 5시
        비서머타임: 저녁 6시
        """
        is_summer = cls.is_summer_time()
        hour = 17 if is_summer else 18
        label = "저녁 5시" if is_summer else "저녁 6시"
        return hour, label

    @classmethod
    def get_market_hours_kst(cls) -> dict:
        """미국 장 KST 시간표"""
        is_summer = cls.is_summer_time()
        start_hour = 17 if is_summer else 18
        end_hour = 5 if is_summer else 6  # 다음날

        return {
            "is_summer_time": is_summer,
            "kst_premarket_start": f"{start_hour}:00",
            "kst_regular_start": f"다음날 0{(start_hour + 9) % 24}:30",
            "kst_regular_end": f"다음날 {end_hour}:00",
            "kst_aftermarket_end": f"다음날 {end_hour + 4}:00",
            "summer_label": "서머타임" if is_summer else "비서머타임",
        }

    # ========== ⭐ KST 검증 (디버깅/모니터링) ==========

    @classmethod
    def verify_kst(cls) -> TimeVerificationResult:
        """
        현재 KST 설정이 정확한지 검증
        
        3가지 방법 대조:
        1. pytz UTC→KST 변환 (신뢰)
        2. time.gmtime() + 9시간 (POSIX C API)
        3. os.environ['TZ'] 체크
        
        Returns:
            TimeVerificationResult: ok=True면 KST 정상
        """
        cls._init_zones()

        warnings: List[str] = []
        calc_method = "unknown"
        kst_now = cls.get_korea_time()

        # 방법 1: pytz 직접 계산
        if cls._use_pytz:
            utc_now = datetime.now(cls._utc_zone)
            kst_from_utc = utc_now.astimezone(cls._kst_zone)
            offset_sec = kst_from_utc.utcoffset().total_seconds() if kst_from_utc.utcoffset() else 0

            if abs(offset_sec - KST_OFFSET_SECONDS) > 60:
                warnings.append(f"pytz 오프셋 이상: {offset_sec}초")
            else:
                calc_method = "pytz UTC→KST"
        else:
            warnings.append("pytz 미설치, 수동 계산 중")

        # 방법 2: time모듀 gmtime + 수동 +9
        try:
            utc_stamp = timegm(time.gmtime())
            manual_kst = datetime.utcfromtimestamp(utc_stamp) + timedelta(seconds=KST_OFFSET_SECONDS)
            diff_secs = abs((kst_now - manual_kst).total_seconds())
            if diff_secs > 60:
                warnings.append(f"수동 계산과 {diff_secs:.0f}초 차이")
        except Exception as e:
            warnings.append(f"수동 검증 실패: {e}")

        # 방법 3: 환경변수 체크
        env_tz = os.environ.get('TZ', 'UNSET')
        if env_tz != KST_ZONE_NAME:
            warnings.append(f"TZ 환경변수={env_tz}, Seoul 아님")

        # 오프셋 계산
        if cls._use_pytz and kst_now.tzinfo:
            offset_hours = kst_now.utcoffset().total_seconds() / 3600 if kst_now.utcoffset() else 0
        else:
            # tzinfo 없으면 +9 고정
            offset_hours = 9.0

        # OK 조건: offset이 +9에 근접하고, 경고 없음
        is_ok = (abs(offset_hours - 9.0) < 0.1) and len(warnings) == 0

        if not is_ok and not warnings:
            warnings.append("상태 확인 필요")

        return TimeVerificationResult(
            ok=is_ok,
            kst_now_str=kst_now.strftime("%Y-%m-%d %H:%M:%S KST"),
            utc_now_str=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            offset_hours=offset_hours,
            server_tz_env=env_tz,
            calc_method=calc_method,
            warning="; ".join(warnings) if warnings else None,
        )

    @classmethod
    def format_time_info(cls) -> str:
        """텔레그램/로그용 시간 정보 문자열"""
        v = cls.verify_kst()
        hours = cls.get_market_hours_kst()

        lines = [
            f"🕐 현재: {v.kst_now_str}",
            f"🌍 UTC: {v.utc_now_str}",
            f"⏱️ 오프셋: UTC{v.offset_hours:+.1f}",
            f"🔧 계산: {v.calc_method}",
        ]

        if not v.ok:
            lines.append(f"⚠️ 경고: {v.warning}")

        lines.extend([
            f"",
            f"📅 뉴욕장 ({hours['summer_label']})",
            f"프리장 시작: {hours['kst_premarket_start']}",
            f"정규장 마감: {hours['kst_regular_end']}",
            f"애프터장 마감: {hours['kst_aftermarket_end']}",
        ])

        return "\n".join(lines)

    @classmethod
    def assert_kst(cls):
        """
        KST 아니면 예외 발생 (보수적 방어)
        봇 스타트 시 필수 체크용
        """
        v = cls.verify_kst()
        if not v.ok:
            raise RuntimeError(
                f"KST 검증 실패: {v.warning}\n"
                f"현재 서버 시간: {v.kst_now_str}\n"
                f"TZ 환경변수: {v.server_tz_env}\n"
                f"서버를 한국 시간으로 설정하세요."
            )
        return v


# ========== 유틸리티: time.gmtime 대체 ==========

def timegm(tuple_tuple) -> int:
    """time.gmtime → unix timestamp (calendar.timegm 대체)"""
    return int(
        (datetime(*tuple_tuple[:6]) - datetime(1970, 1, 1)).total_seconds()
    )


# ========== 모듈 로드 즉시 검증 ==========
if __name__ == "__main__":
    # 단독 실행 시 테스트
    print(MarketTime.format_time_info())
    print("\n--- 검증 결과 ---")
    result = MarketTime.verify_kst()
    print(f"OK: {result.ok}")
    print(f"경고: {result.warning}")
