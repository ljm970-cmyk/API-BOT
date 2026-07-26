from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum

class OrderType(Enum):
    LOC = "LOC"
    MOC = "MOC"        # 장마감 시장가 (리버스모드 첫날)
    LIMIT = "LIMIT"    # 지정가 (GTC - 프리~애프터)

class BuyTag(Enum):
    STAR_BUY = "star_buy"
    AVG_BUY = "avg_buy"
    CRASH_BUY = "crash_buy"
    BIG_NUMBER = "big_number"

class SellTag(Enum):
    QUARTER_SELL = "quarter_sell"   # LOC/MOC 쿼터
    FINAL_SELL = "final_sell"        # 지정가 목표매도

@dataclass
class OrderItem:
    """개별 주문 항목"""
    price: float
    quantity: int
    tag: str              # star_buy, avg_buy, crash_buy, quarter_sell, final_sell 등
    order_type: OrderType = OrderType.LOC
    note: str = ""        # 표시용 메모
    
    def format_line(self) -> str:
        """표시용 한 줄"""
        if self.quantity == 1 and "crash" in self.tag:
            return f"  ${self.price:.2f} x {self.quantity}주"
        return f"  ${self.price:.2f} x {self.quantity}주 ({self.tag})"

@dataclass
class DailyOrderPlan:
    """사진과 동일한 구조의 일일 계획"""
    
    stock_code: str
    mode: str = "일반모드"  # 일반모드 / 리버스모드
    
    # 현재 상태
    shares_held: int = 0
    avg_price: float = 0
    current_price: float = 0
    t_value: float = 0
    
    # 매수 목록
    loc_buys: List[OrderItem] = field(default_factory=list)
    crash_buys: List[OrderItem] = field(default_factory=list)
    
    # 매도 목록
    quarter_sell: Optional[OrderItem] = None    # LOC/MOC
    final_sell: Optional[OrderItem] = None       # 지정가
    
    # 메타
    star_point: float = 0
    target_price: float = 0
    daily_buy_amount: float = 0
    
    @property
    def is_reverse(self) -> bool:
        return self.mode == "리버스모드"
    
    @property
    def total_buy_shares(self) -> int:
        total = sum(o.quantity for o in self.loc_buys)
        total += sum(o.quantity for o in self.crash_buys)
        return total
    
    def format_telegram_report(self) -> str:
        """
        사진과 동일한 형식으로 리포트 생성
        """
        lines = [
            f"[TQQQ 무한매수법 v4.0 리포트] ({self.mode})",
            "",
            f"보유 수량: {self.shares_held}주",
            f"평균단가: ${self.avg_price:.2f}",
            f"현재가: ${self.current_price:.2f}",
            f"T값: {self.t_value:.4f}",
        ]
        
        # LOC 매수
        if self.loc_buys:
            lines.extend(["", "[LOC 매수]"])
            for o in self.loc_buys:
                lines.append(o.format_line())
        
        # 폭락장 대비 (crash buys)
        if self.crash_buys:
            lines.extend(["", "[폭락장 대비 추가매수 (LOC, 1주씩)]"])
            for o in self.crash_buys:
                lines.append(o.format_line())
        
        # 매도
        if self.quarter_sell:
            order_type_name = "LOC/MOC"
            if self.is_reverse and not self.quarter_sell.order_type == OrderType.MOC:
                order_type_name = "LOC"
            lines.extend(["", f"[{order_type_name} 매도]"])
            lines.append(self.quarter_sell.format_line())
        
        # 지정가 매도
        if self.final_sell:
            lines.extend(["", "[지정가 매도]"])
            lines.append(self.final_sell.format_line())
            lines.append(f"  (목표: ${self.target_price:.2f})")
        
        return "\n".join(lines)
    
    def format_execution_result(self, executed_buys: List[str], executed_sells: List[str]) -> str:
        """
        체결 결과 표시
        
        executed_buys: ["star_buy", "avg_buy", "crash_buy_1"] 등 성공한 tag 목록
        executed_sells: ["quarter_sell", "final_sell"] 등
        """
        lines = [f"[TQQQ 매수 주문 실행 결과]"]
        
        # 매수 결과
        for o in self.loc_buys + self.crash_buys:
            status = "✅" if o.tag in executed_buys else "⬜"
            lines.append(f"{status} {o.tag}: ${o.price:.2f} x {o.quantity}주")
        
        # 매도 결과  
        for o in [self.quarter_sell, self.final_sell]:
            if o is None:
                continue
            status = "✅" if o.tag in executed_sells else "⬜"
            lines.append(f"{status} {o.tag}: ${o.price:.2f} x {o.quantity}주")
        
        return "\n".join(lines)
