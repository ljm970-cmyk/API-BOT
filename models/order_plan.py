from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(Enum):
    LOC = "LOC"
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    MOC = "MOC"

@dataclass
class SingleOrder:
    side: OrderSide
    order_type: OrderType
    price: float
    quantity: int
    is_quarter: bool = False
    is_crash: bool = False
    is_big_number: bool = False

@dataclass
class DailyOrderPlan:
    date: str
    loc_buys: List[SingleOrder] = None
    loc_quarter_sell: Optional[SingleOrder] = None
    limit_target_sell: Optional[SingleOrder] = None
    moc_sell: Optional[SingleOrder] = None
    star_point: float = 0
    target_sell_price: float = 0

    def __post_init__(self):
        if self.loc_buys is None:
            self.loc_buys = []
