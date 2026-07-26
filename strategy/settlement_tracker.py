from datetime import datetime
from typing import Optional
from models.settlement import SettlementRecord, SettlementHistory
from models.position import Position
from utils.logger import setup_logger
from utils.timezone import MarketTime

logger = setup_logger()


class SettlementTracker:
    """
    사이클 시작 ~ 종료를 추적하여 정산 기록 생성
    """

    def __init__(self):
        self.history = SettlementHistory()
        self._cycle_start_date: Optional[str] = None
        self._cycle_max_t: float = 0
        self._reverse_entered: bool = False
        self._was_in_position: bool = False

    def initialize_from_position(self, position: Position):
        """기존 포지션에서 상태 복원 시 호출"""
        if position.is_first_buy and position.shares_held == 0:
            # 사이클 완전 초기
            self._cycle_start_date = None
        else:
            # 진행 중인 사이클 복원
            self._cycle_start_date = position.buy_records[0].date if position.buy_records else MarketTime.get_korea_time().strftime("%Y%m%d")
            self._cycle_max_t = position.current_t
            self._reverse_entered = position.is_reverse_mode
            self._was_in_position = position.shares_held > 0

    def check_cycle_state(self, position: Position):
        """
        사이클 상태 변화를 감지하여 기록
        
        호출 시점: 매일 장 마객 후
        """
        # 매숭이 늘어나면 max_t 갱신
        if position.current_t > self._cycle_max_t:
            self._cycle_max_t = position.current_t
            logger.debug(f"새로운 최고 T: {self._cycle_max_t:.4f}")
        
        # 리버스모드 진입 여부
        if position.is_reverse_mode:
            self._reverse_entered = True
        
        # 사이클 시작 감지 (처음 매수)
        if position.shares_held > 0 and not self._was_in_position:
            self._cycle_start_date = MarketTime.get_korea_time().strftime("%Y%m%d")
            self._cycle_max_t = position.current_t
            self._reverse_entered = position.is_reverse_mode
            self._was_in_position = True
            logger.info(f"새 사이클 시작: {self._cycle_start_date}, T={self._cycle_max_t}")
        
        # 사이클 종료 감지 (보유 0 + T=0 + 이전에 보유 있었음)
        if position.shares_held == 0 and position.current_t == 0 and self._was_in_position:
            self._record_settlement(position)
            self._reset_cycle()
            self._was_in_position = False
        
        # 사이클 종료 후에도 0 상태 유지
        elif position.shares_held == 0:
            self._was_in_position = False

    def _record_settlement(self, position: Position):
        """정산 기록 저장"""
        if not self._cycle_start_date:
            logger.warning("사이클 시작일 없음, 정산 스킵")
            return
        
        end_date = MarketTime.get_korea_time().strftime("%Y%m%d")
        
        # 수익 계산
        profit = position.remaining_capital - position.total_capital
        return_pct = (profit / position.total_capital) * 100 if position.total_capital > 0 else 0
        
        record = SettlementRecord(
            cycle_id=0,  # 자동 할당
            stock_code=position.stock_code,
            start_date=self._cycle_start_date,
            end_date=end_date,
            total_capital=position.total_capital,
            ending_capital=position.remaining_capital,
            profit_loss=profit,
            return_pct=return_pct,
            max_t=self._cycle_max_t,
            final_t=position.current_t,
            mode="리버스" if self._reverse_entered else "일반",
            reverse_entered=self._reverse_entered,
            total_buys=len([r for r in position.buy_records if not r.is_reverse_buy]),
            total_sells=len([r for r in position.buy_records if r.is_reverse_buy])  # reverse_buy에 sell_count 추가 필요
        )
        
        self.history.add(record)
        logger.info(f"정산 완료: #{record.cycle_id}, 수익률 {return_pct:.2f}%")

    def _reset_cycle(self):
        """새 사이클 준비"""
        self._cycle_start_date = None
        self._cycle_max_t = 0
        self._reverse_entered = False

    def get_summary_text(self) -> str:
        """텔레그램 표시용 전체 요약"""
        return self.history.get_all_summary()
