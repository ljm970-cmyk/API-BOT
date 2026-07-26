import math
from typing import Tuple, List, Optional
from models.position import Position
from models.price_history import PriceHistory
from utils.logger import setup_logger

logger = setup_logger()

class ReverseModeCalculator:
    def __init__(self, position: Position):
        self.position = position
        self.price_hist = PriceHistory(position.stock_code)
        if position.split_count == 20:
            position.reverse_sell_divisor = 10
        else:
            position.reverse_sell_divisor = 20

    def get_star_price(self) -> float:
        avg = self.price_hist.get_five_day_average()
        if avg is None:
            return self.position.avg_price
        return avg

    def calculate_moc_sell(self) -> int:
        total = self.position.shares_held
        div = self.position.reverse_sell_divisor
        qty = math.floor(total / div)
        return max(1, qty) if total > 0 else 0

    def calculate_star_sell(self, remaining: int) -> int:
        div = self.position.reverse_sell_divisor
        qty = math.floor(remaining / div)
        return max(1, qty) if remaining > 0 else 0

    def calculate_quarter_buy(self, previous_inflow: float = 0):
        total_cash = self.position.remaining_capital + previous_inflow
        quarter = total_cash / 4
        star = self.get_star_price()
        buy_below = round(star - 0.01, 2)
        big = round(buy_below * 0.80, 2)
        
        orders = []
        if big > 0 and quarter > 0:
            big_qty = max(1, int(quarter / big))
            orders.append((big, big_qty, "big_number"))
        
        if buy_below > 0 and quarter > 0:
            main_qty = max(1, int(quarter / buy_below))
            orders.append((buy_below, main_qty, "star_below"))
        
        return quarter, orders

    def update_t_value(self, is_sell: bool = False, is_buy: bool = False) -> float:
        t = self.position.current_t
        n = 20 if self.position.split_count == 20 else 40
        if is_sell:
            new_t = t * (0.9 if n == 20 else 0.95)
        elif is_buy:
            new_t = t + (n - t) * 0.25
        else:
            new_t = t
        return round(new_t, 6)

    def process_executions(self, sell_executed: bool = False, sell_price: float = 0,
                          sell_qty: int = 0, buy_executions: list = None):
        buy_executions = buy_executions or []
        
        if sell_executed:
            self.position.shares_held -= sell_qty
            self.position.remaining_capital += sell_price * sell_qty
            self.position.current_t = self.update_t_value(is_sell=True)
            if self.position.reverse_day_count == 0:
                self.position.reverse_first_sell_done = True

        total_buy_val = 0
        total_buy_qty = 0
        for price, qty, btype in buy_executions:
            total_buy_val += price * qty
            total_buy_qty += qty
            self.position.buy_records.append(BuyRecord(
                date=datetime.now().strftime("%Y%m%d"),
                price=price, quantity=qty, amount=price*qty,
                is_crash_buy=('crash' in btype), is_reverse_buy=True,
                t_at_buy=self.position.current_t
            ))
            self.position.remaining_capital -= price * qty

        if total_buy_qty > 0:
            old_val = self.position.avg_price * self.position.shares_held
            new_shares = self.position.shares_held + total_buy_qty
            self.position.avg_price = round((old_val + total_buy_val) / new_shares, 2) if new_shares > 0 else 0
            self.position.shares_held = new_shares
            self.position.current_t = self.update_t_value(is_buy=True)

        return self.position
