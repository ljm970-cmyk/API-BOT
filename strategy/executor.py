import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from models.position import Position, BuyRecord
from strategy.calculator import InfiniteBuyCalculator
from utils.timezone import MarketTime
from utils.logger import setup_logger

logger = setup_logger()

class InfiniteBuyExecutor:
    STATE_FILE = "data/state.json"

    def __init__(self, client, stock_code: str, split_count: int, total_capital: float):
        self.client = client
        self.calculator = InfiniteBuyCalculator(stock_code, split_count)
        self.position = self._load_or_create(stock_code, split_count, total_capital)
        self.today_plan = None

    def _load_or_create(self, code: str, split: int, capital: float) -> Position:
        if os.path.exists(self.STATE_FILE):
            try:
                with open(self.STATE_FILE, 'r') as f:
                    data = json.load(f)
                    if data.get("stock_code") == code:
                        return Position.from_dict(data)
            except Exception as e:
                logger.warning(f"상태 복원 실패: {e}")
        return Position(
            stock_code=code, stock_name="TQQQ" if "TQQQ" in code else "SOXL",
            total_capital=capital, split_count=split, remaining_capital=capital
        )

    def save_state(self):
        os.makedirs("data", exist_ok=True)
        # 한국 시간 timestamp 추가
        data = self.position.to_dict()
        data["_saved_at"] = MarketTime.format_korea_now()
        
        with open(self.STATE_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def get_current_kst_log(self) -> str:
        """상태 저장 시 시간 기록"""
        return f"[{MarketTime.format_korea_now()}]"

    def set_limit_order_time(self):
        """
        지정가매도 추천 시간 확인 [1]
        
        프리장이 시작하는 저녁 5시(서머타임) or 6시(비서머타임)
        """
        hour, label = MarketTime.get_limit_order_deadline_kst()
        now = MarketTime.get_korea_time()
        
        if now.hour < 12:  # 오전 중에는 알림
            return f"오늘 저녁 {label}에 지정가매도를 걸어두세요"
        
        if now.hour == hour:  # 지금이 적정 시간
            return f"지금({label})이 지정가매도를 걸기 가장 효율적인 시간입니다"
        
        if now.hour > hour and now.hour < 24:  # 이미 지남
            next_day = "내일" if now.hour >= 0 else "오늘"
            return f"{next_day} {label}에 다음 지정가매도를 걸어두세요"
        
        return ""

    def generate_daily_plan(self, current_price: float) -> str:
        # 시간 정보
        kst_now = MarketTime.get_korea_time()
        time_str = kst_now.strftime("%m/%d %H:%M")
        
        # 지정가매도 시간 추천
        limit_msg = self.set_limit_order_time()
        
        plan = self._create_plan(current_price)
        
        result = f"[{time_str} KST]\n{plan}"
        if limit_msg:
            result += f"\n\n⏰ {limit_msg}"
        
        self.save_state()
        return result

    def _create_plan(self, current_price: float) -> str:
        # (기존 계획 생성 로직)
        return f"T={self.position.current_t:.4f}, 잔금=${self.position.remaining_capital:.2f}"

    def update_after_market(self, executions: List[tuple]):
        # 체결 처리 + 시간 기록
        # (기존 로직)
        
        # 체결 결과에 시간 추가
        kst = MarketTime.get_korea_time()
        self.position.buy_records.append(BuyRecord(
            date=kst.strftime("%Y%m%d"),
            price=0, quantity=0, amount=0,  # 실제 값으로 대체
            t_at_buy=self.position.current_t
        ))
        
        self.save_state()
        return self.position.to_dict()
