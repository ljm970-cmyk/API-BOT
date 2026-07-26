from typing import List, Tuple
from models.position import Position

class InfiniteBuyCalculator:
    def __init__(self, stock_code: str, split_count: int):
        self.stock_code = stock_code.upper()
        self.split_count = split_count
        assert split_count in [20, 40], "분할수는 20 또는 40"

    def get_star_percent(self, t: float) -> float:
        if "TQQQ" in self.stock_code:
            return (15 - 1.5 * t) if self.split_count == 20 else (15 - 0.75 * t)
        return (20 - 2 * t) if self.split_count == 20 else (20 - t)

    def get_star_price(self, avg_price: float, t: float) -> float:
        star_pct = self.get_star_percent(t)
        return round(avg_price * (1 + star_pct / 100), 2)

    def get_target_sell_price(self, avg_price: float) -> float:
        multiplier = 1.15 if "TQQQ" in self.stock_code else 1.20
        return round(avg_price * multiplier, 2)

    def get_daily_buy_amount(self, remaining: float, current_t: float) -> float:
        divisor = self.split_count - current_t
        if divisor <= 0:
            return remaining
        return round(remaining / divisor, 2)

    @staticmethod
    def apply_full_buy(t: float):
        return t + 1.0

    @staticmethod
    def apply_half_buy(t: float):
        return t + 0.5

    @staticmethod
    def apply_quarter_sell(t: float):
        return t * 0.75

    @staticmethod
    def apply_after_limit_sell_then_loc_buy(t: float, is_full_buy: bool):
        return (t * 0.25 + 1.0) if is_full_buy else (t * 0.25 + 0.5)

    def calculate_first_buy(self, daily_amount: float, price: float, big_price: float) -> List[Tuple[float, int, str]]:
        orders = []
        qty = int(daily_amount / big_price)
        if qty > 0:
            orders.append((big_price, qty, "main"))
        for i, div in enumerate(range(13, 18)):
            crash_price = round(daily_amount / div, 2)
            if crash_price > 0:
                orders.append((crash_price, 1, f"crash_{i+1}"))
        return orders

    def calculate_first_half_buy(self, daily_amount: float, star_price: float, avg_price: float) -> List[Tuple[float, int, str]]:
        half = daily_amount / 2
        star_qty = max(1, int(half / star_price))
        avg_qty = max(1, int(half / avg_price))
        total = star_qty + avg_qty
        if total % 2 == 1:
            avg_qty += 1
        
        orders = [(round(star_price - 0.01, 2), star_qty, "star")]
        orders.append((round(avg_price, 2), avg_qty, "avg"))
        
        used = sum(p*q for p,q,_ in orders)
        remaining = daily_amount - used
        if remaining > 0:
            extra = round(avg_price * 0.95, 2)
            extra_qty = max(1, int(remaining / extra))
            orders.append((extra, extra_qty, "extra"))
        return orders

    def calculate_second_half_buy(self, daily_amount: float, star_price: float) -> List[Tuple[float, int, str]]:
        buy_price = round(star_price - 0.01, 2)
        qty = max(1, int(daily_amount / buy_price))
        orders = [(buy_price, qty, "star")]
        
        remaining = daily_amount - (buy_price * qty)
        ratio = 0.95
        while remaining > buy_price * 0.5 and len(orders) < 5:
            extra = round(buy_price * ratio, 2)
            extra_qty = 1
            orders.append((extra, extra_qty, "crash_extra"))
            remaining -= extra
            ratio -= 0.03
        return orders

    def calculate_quarter_sell(self, shares_held: int) -> int:
        return max(1, int(shares_held / 4))
