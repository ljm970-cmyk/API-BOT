from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class BuyRecord:
    date: str
    price: float
    quantity: int
    amount: float
    is_crash_buy: bool = False
    t_at_buy: float = 0
    is_reverse_buy: bool = False

@dataclass  
class Position:
    stock_code: str
    stock_name: str
    total_capital: float
    split_count: int
    current_t: float = 0
    remaining_capital: float = 0
    shares_held: int = 0
    avg_price: float = 0
    buy_records: List[BuyRecord] = field(default_factory=list)
    last_quarter_sell_date: Optional[str] = None
    is_first_buy: bool = True
    is_reverse_mode: bool = False
    reverse_day_count: int = 0
    reverse_first_sell_done: bool = False
    reverse_sell_divisor: int = 0

    def __post_init__(self):
        if self.remaining_capital == 0 and self.total_capital > 0:
            self.remaining_capital = self.total_capital

    @property
    def is_exhausted(self) -> bool:
        return self.current_t >= (self.split_count - 1)

    @property
    def should_enter_reverse(self) -> bool:
        if self.split_count == 20:
            return self.current_t > 19
        return self.current_t > 39

    def check_reverse_exit(self, today_close: float) -> bool:
        if self.avg_price <= 0:
            return False
        if "TQQQ" in self.stock_code:
            threshold = self.avg_price * 0.85
        else:
            threshold = self.avg_price * 0.80
        return today_close <= threshold

    def reset_for_normal(self):
        self.is_reverse_mode = False
        self.reverse_day_count = 0
        self.reverse_first_sell_done = False

    def to_dict(self) -> dict:
        return {
            "stock_code": self.stock_code,
            "total_capital": self.total_capital,
            "split_count": self.split_count,
            "current_t": self.current_t,
            "remaining_capital": self.remaining_capital,
            "shares_held": self.shares_held,
            "avg_price": self.avg_price,
            "buy_records": [
                {
                    "date": r.date, "price": r.price, "quantity": r.quantity,
                    "amount": r.amount, "is_crash_buy": r.is_crash_buy,
                    "t_at_buy": r.t_at_buy, "is_reverse_buy": r.is_reverse_buy
                } for r in self.buy_records
            ],
            "last_quarter_sell_date": self.last_quarter_sell_date,
            "is_first_buy": self.is_first_buy,
            "is_reverse_mode": self.is_reverse_mode,
            "reverse_day_count": self.reverse_day_count,
            "reverse_first_sell_done": self.reverse_first_sell_done,
            "reverse_sell_divisor": self.reverse_sell_divisor,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        records = []
        for r in data.get("buy_records", []):
            rec = BuyRecord(
                date=r["date"], price=r["price"], quantity=r["quantity"],
                amount=r["amount"], is_crash_buy=r.get("is_crash_buy", False),
                t_at_buy=r.get("t_at_buy", 0),
                is_reverse_buy=r.get("is_reverse_buy", False)
            )
            records.append(rec)
        
        pos = cls(
            stock_code=data["stock_code"],
            stock_name=data.get("stock_name", ""),
            total_capital=data["total_capital"],
            split_count=data["split_count"],
            current_t=data.get("current_t", 0),
            remaining_capital=data.get("remaining_capital", data["total_capital"]),
            shares_held=data.get("shares_held", 0),
            avg_price=data.get("avg_price", 0),
            buy_records=records,
            last_quarter_sell_date=data.get("last_quarter_sell_date"),
            is_first_buy=data.get("is_first_buy", True),
            is_reverse_mode=data.get("is_reverse_mode", False),
            reverse_day_count=data.get("reverse_day_count", 0),
            reverse_first_sell_done=data.get("reverse_first_sell_done", False),
            reverse_sell_divisor=data.get("reverse_sell_divisor", 0),
        )
        return pos
