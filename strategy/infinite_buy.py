from models.position import Position
from models.price_history import PriceHistory
from strategy.calculator import InfiniteBuyCalculator
from strategy.executor import InfiniteBuyExecutor
from strategy.reverse_mode import ReverseModeCalculator
from utils.logger import setup_logger

logger = setup_logger()

class InfiniteBuyStrategy:
    def __init__(self, client, stock_code: str, split_count: int, total_capital: float):
        self.client = client
        self.stock_code = stock_code
        self.split_count = split_count
        self.executor = InfiniteBuyExecutor(client, stock_code, split_count, total_capital)
        self.position = self.executor.position
        self.normal_calc = InfiniteBuyCalculator(stock_code, split_count)
        self.reverse_calc = None
        self.price_hist = PriceHistory(stock_code)
        self._check_mode_transition()

    def _check_mode_transition(self):
        if not self.position.is_reverse_mode and self.position.should_enter_reverse:
            logger.warning(f"리버스모드 진입: T={self.position.current_t}")
            self._enter_reverse_mode()

    def _enter_reverse_mode(self):
        self.position.is_reverse_mode = True
        self.position.reverse_day_count = 0
        self.position.reverse_first_sell_done = False
        self.reverse_calc = ReverseModeCalculator(self.position)

    def check_reverse_exit(self, today_close: float) -> bool:
        if not self.position.is_reverse_mode:
            return False
        if self.position.check_reverse_exit(today_close):
            self._exit_reverse_mode()
            return True
        return False

    def _exit_reverse_mode(self):
        self.position.reset_for_normal()
        self.executor.save_state()
        logger.info(f"일반모드 복귀: T={self.position.current_t}")

    def generate_today_plan(self, current_price: float, today_close: float = 0,
                           yesterday_sell_proceeds: float = 0):
        if today_close > 0 and self.position.is_reverse_mode:
            exited = self.check_reverse_exit(today_close)
            if exited:
                return {"mode": "reverse_to_normal"}

        if self.position.is_reverse_mode:
            if not self.reverse_calc:
                self.reverse_calc = ReverseModeCalculator(self.position)
            day = self.position.reverse_day_count + 1

            # (생략 - 실제 plan 생성)
            self.price_hist.add_close(
                __import__('datetime').datetime.now().strftime("%Y%m%d"), current_price)
            return {"mode": "reverse", "day": day}

        plan = self.executor.generate_daily_plan(current_price)
        self.price_hist.add_close(
            __import__('datetime').datetime.now().strftime("%Y%m%d"), current_price)
        return {"mode": "normal", "summary": plan}
