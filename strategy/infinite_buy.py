from models.position import Position
from models.price_history import PriceHistory
from strategy.calculator import InfiniteBuyCalculator
from strategy.executor import InfiniteBuyExecutor
from strategy.reverse_mode import ReverseModeCalculator
from strategy.settlement_tracker import SettlementTracker  # ⭐ 추가
from utils.logger import setup_logger

logger = setup_logger()

class InfiniteBuyStrategy:
    def __init__(self, client, stock_code: str, split_count: int, total_capital: float):
        self.client = client
        self.stock_code = stock_code
        self.split_count = split_count
        
        self.executor = InfiniteBuyExecutor(client, stock_code, split_count, total_capital)
        self.position = self.executor.position
        
        self.calculator = InfiniteBuyCalculator(stock_code, split_count)
        self.reverse_calc = None
        self.price_hist = PriceHistory(stock_code)
        
        # ⭐ 정산 트래커 연결
        self.settlement_tracker = SettlementTracker()
        self.settlement_tracker.initialize_from_position(self.position)
        
        self._check_mode_transition()

    def update_after_execution(self, plan, executed_buys: list, executed_sells: list):
        """
        체결 후 호출 (executor 대신 unified interface)
        """
        # 기존 상태 업데이트
        self.executor.update_after_buy(plan, executed_buys)
        self.executor.update_after_sell(plan, executed_sells)
        
        # ⭐ 정산 트래커 확인 (사이클 종료 감지)
        self.settlement_tracker.check_cycle_state(self.position)
        
        # 리버스/일반 모드 전환 확인
        if not self.position.is_reverse_mode and self.position.should_enter_reverse:
            self._enter_reverse_mode()
