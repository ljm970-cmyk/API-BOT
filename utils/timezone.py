#!/usr/bin/env python3
"""
KST(한국 시간) 영구 고정 유틸리티
서버 TZ 변경, 재부팅, 여름/겨울 시기 전환에도 정확한 KST 보장
"""

import os
import time
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
    ok: bool
    kst_now_str: str
    utc_now_str: str
    offset_hours: float
    server_tz_env: str
    calc_method: str
    warning: Optional[str] = None


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

    @classmethod
    def get_korea_time(cls) -> datetime:
        """
        현재 KST 시간 - 서버 TZ 설정과 무관
        UTC 기준 → KST 변환
        """
        cls._init_zones()

        if cls._use_pytz:
            utc_now = datetime.now(cls._utc_zone)
            kst_now = utc_now.astimezone(cls._kst_zone)
            return kst_now.replace(tzinfo=None)
        else:
            utc_now = datetime.utcnow()
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

    @classmethod
    def is_summer_time(cls, date: Optional[datetime] = None) -> bool:
        """
        뉴욕 서머타임 여부
        """
        cls._init_zones()
        now = date or cls.get_korea_time()

        if cls._use_pytz:
            et_zone = pytz.timezone('US/Eastern')
            et_now = et_zone.localize(now.replace(tzinfo=None))
            return bool(et_now.dst())

        year = now.year
        march = datetime(year, 3, 8)
        dst_start = march + timedelta(days=(6 - march.weekday()) % 7 + 7)
        nov = datetime(year, 11, 1)
        dst_end = nov + timedelta(days=(6 - nov.weekday()) % 7)

        return dst_start <= now.replace(tzinfo=None) < dst_end

    @classmethod
    def get_limit_order_deadline_kst(cls) -> Tuple[int, str]:
        """지정가매도 권장 시간"""
        is_summer = cls.is_summer_time()
        hour = 17 if is_summer else 18
        label = "저녁 5시" if is_summer else "저녁 6시"
        return hour, label

    @classmethod
    def get_market_hours_kst(cls) -> dict:
        """미국 장 KST 시간표"""
        is_summer = cls.is_summer_time()
        start_hour = 17 if is_summer else 18
        end_hour = 5 if is_summer else 6

        return {
            "is_summer_time": is_summer,
            "kst_premarket_start": f"{start_hour}:00",
            "kst_regular_start": f"다음날 0{(start_hour + 9) % 24}:30",
            "kst_regular_end": f"다음날 {end_hour}:00",
            "kst_aftermarket_end": f"다음날 {end_hour + 4}:00",
            "summer_label": "서머타임" if is_summer else "비서머타임",
        }

    @classmethod
    def verify_kst(cls) -> TimeVerificationResult:
        """
        KST 정확성 3중 검증
        """
        cls._init_zones()

        warnings: List[str] = []
        calc_method = "unknown"
        kst_now = cls.get_korea_time()

        # 방법 1: pytz
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

        # 방법 2: 수동 검증
        try:
            import calendar
            utc_stamp = calendar.timegm(time.gmtime())
            manual_kst = datetime.utcfromtimestamp(utc_stamp) + timedelta(seconds=KST_OFFSET_SECONDS)
            diff_secs = abs((kst_now - manual_kst).total_seconds())
            if diff_secs > 60:
                warnings.append(f"수동 계산과 {diff_secs:.0f}초 차이")
        except Exception as e:
            warnings.append(f"수동 검증 실패: {e}")

        # 방법 3: 환경변수
        env_tz = os.environ.get('TZ', 'UNSET')
        if env_tz != KST_ZONE_NAME:
            warnings.append(f"TZ 환경변수={env_tz}")

        # 결과
        if cls._use_pytz and kst_now.tzinfo:
            offset_hours = kst_now.utcoffset().total_seconds() / 3600 if kst_now.utcoffset() else 0
        else:
            offset_hours = 9.0

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
        """텔레그램/로그 출력용"""
        v = cls.verify_kst()
        h = cls.get_market_hours_kst()

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
            f"📅 뉴욕장 ({h['summer_label']})",
            f"프리장: {h['kst_premarket_start']}",
            f"정규장마감: {h['kst_regular_end']}",
            f"애프터장마감: {h['kst_aftermarket_end']}",
        ])

        return "\n".join(lines)

    @classmethod
    def assert_kst(cls):
        """KST 아니면 RuntimeError"""
        v = cls.verify_kst()
        if not v.ok:
            raise RuntimeError(
                f"KST 검증 실패: {v.warning}\n"
                f"서버 시간: {v.kst_now_str}\n"
                f"TZ 환경변수: {v.server_tz_env}\n"
                f"서버를 한국 시간으로 설정하세요."
            )
        return v


# ========== 모듈 로드 시 자동 검증 (선택) ==========
if __name__ == "__main__":
    print(MarketTime.format_time_info())
    print("\n--- 검증 ---")
    r = MarketTime.verify_kst()
    print(f"OK: {r.ok}")
    if r.warning:
        print(f"경고: {r.warning}")
