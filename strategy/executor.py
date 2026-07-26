import json
import os
from datetime import datetime
from typing import List, Dict, Any
from models.position import Position, BuyRecord
from strategy.calculator import InfiniteBuyCalculator
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
        return Position(stock_code=code, stock_name="TQQQ" if "TQQQ" in code else "SOXL",
                       total_capital=capital, split_count=split, remaining_capital=capital)

    def save_state(self):
        os.makedirs("data", exist_ok=True)
        with open(self.STATE_FILE, 'w') as f:
            json.dump(self.position.to_dict(), f, indent=2, default=str)

    def generate_daily_plan(self, current_price: float) -> str:
        # (생략 - 실제 구현)
        self.save_state()
        return f"T={self.position.current_t}, 자금={self.position.remaining_capital}, 보유={self.position.shares_held}"

    def update_after_market(self, executions: List[tuple]):
        # (생략 - 실제 구현)
        self.save_state()
        return self.position.to_dict()
