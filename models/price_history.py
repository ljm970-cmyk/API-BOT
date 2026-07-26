import json
import os
from collections import deque
from typing import Optional

class PriceHistory:
    FILE = "data/price_history.json"
    MAX_DAYS = 5

    def __init__(self, stock_code: str):
        self.stock_code = stock_code.upper()
        self.prices = deque(maxlen=self.MAX_DAYS)
        self._load()

    def _load(self):
        if not os.path.exists(self.FILE):
            return
        try:
            with open(self.FILE, 'r') as f:
                all_data = json.load(f)
                data = all_data.get(self.stock_code, [])
                self.prices = deque(data, maxlen=self.MAX_DAYS)
        except:
            self.prices = deque(maxlen=self.MAX_DAYS)

    def _save(self):
        os.makedirs("data", exist_ok=True)
        all_data = {}
        if os.path.exists(self.FILE):
            with open(self.FILE, 'r') as f:
                try:
                    all_data = json.load(f)
                except:
                    pass
        
        all_data[self.stock_code] = list(self.prices)
        with open(self.FILE, 'w') as f:
            json.dump(all_data, f, indent=2)

    def add_close(self, date: str, close_price: float):
        if self.prices and self.prices[-1][0] == date:
            self.prices.pop()
        self.prices.append((date, round(close_price, 2)))
        self._save()

    def get_five_day_average(self) -> Optional[float]:
        if len(self.prices) == 0:
            return None
        recent = list(self.prices)[-5:]
        avg = sum(p[1] for p in recent) / len(recent)
        return round(avg, 2)
