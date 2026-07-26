import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from utils.logger import setup_logger

logger = setup_logger()


@dataclass
class SettlementRecord:
    """
    하나의 사이클이 종료된 후 기록되는 정산 데이터
    """
    cycle_id: int                   # 사이클 순번
    stock_code: str                 # TQQQ / SOXL
    
    start_date: str                 # 사이클 시작일
    end_date: str                   # 사이클 종료일
    
    total_capital: float            # 시작 원금
    ending_capital: float           # 종료 시 잔금
    
    profit_loss: float              # 순수익
    return_pct: float               # 수익률 %
    
    max_t: float                    # 사이클 중 최고 T값
    final_t: float                  # 종료 시 T값 (보통 0)
    
    mode: str                       # 마지막 모드: 일반 / 리버스
    
    # 추가 상세
    total_buys: int = 0             # 총 매수 횟수
    total_sells: int = 0            # 총 매도 횟수
    reverse_entered: bool = False   # 리버스모드 진입 여부
    
    # 포지션 종료 시점 정보
    shares_held: int = 0            # 종료 시 보유 (0)
    avg_price: float = 0            # 마지막 평균단가
    
    def __post_init__(self):
        self.profit_loss = round(self.profit_loss, 2)
        self.return_pct = round(self.return_pct, 4)
    
    @property
    def duration_days(self) -> int:
        """사이클 소요 일수"""
        try:
            start = datetime.strptime(self.start_date, "%Y%m%d")
            end = datetime.strptime(self.end_date, "%Y%m%d")
            return (end - start).days
        except:
            return 0

    def format_summary(self) -> str:
        """목록 표시용 1줄"""
        emoji = "🟢" if self.profit_loss >= 0 else "🔴"
        return (
            f"{emoji} #{self.cycle_id} {self.stock_code} | "
            f"{self.return_pct:+.2f}% | "
            f"{self.duration_days}일 | "
            f"${self.profit_loss:+.2f}"
        )

    def format_telegram_detail(self) -> str:
        """
        텔레그램 상세 리포트 (사진 스타일 그대로)
        """
        lines = [
            f"📊 [TQQQ 무한매수법 정산 리포트]" if "TQQQ" in self.stock_code else f"📊 [SOXL 무한매수법 정산 리포트]",
            f"",
            f"사이클: #{self.cycle_id}",
            f"종목: {self.stock_code}",
            f"",
            f"📅 기간: {self.start_date} ~ {self.end_date}",
            f"소요일: {self.duration_days}일",
            f"",
            f"💰 시작 원금: ${self.total_capital:,.2f}",
            f"💰 종료 잔금: ${self.ending_capital:,.2f}",
            f"",
            f"📈 순수익: ${self.profit_loss:+.2f}",
            f"📈 수익률: {self.return_pct:+.2f}%",
            f"",
            f"T값 변화: {self.max_t:.4f} → {self.final_t:.4f}",
            f"최고 모드: {'리버스' if self.reverse_entered else '일반'}",
        ]
        
        if self.reverse_entered:
            lines.append(f"⚠️ 리버스모드 진입 후 회복")
        
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "cycle_id": self.cycle_id,
            "stock_code": self.stock_code,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "total_capital": self.total_capital,
            "ending_capital": self.ending_capital,
            "profit_loss": self.profit_loss,
            "return_pct": self.return_pct,
            "max_t": self.max_t,
            "final_t": self.final_t,
            "mode": self.mode,
            "total_buys": self.total_buys,
            "total_sells": self.total_sells,
            "reverse_entered": self.reverse_entered,
            "shares_held": self.shares_held,
            "avg_price": self.avg_price,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SettlementRecord":
        return cls(
            cycle_id=data.get("cycle_id", 0),
            stock_code=data.get("stock_code", "TQQQ"),
            start_date=data.get("start_date", ""),
            end_date=data.get("end_date", ""),
            total_capital=data.get("total_capital", 0),
            ending_capital=data.get("ending_capital", 0),
            profit_loss=data.get("profit_loss", 0),
            return_pct=data.get("return_pct", 0),
            max_t=data.get("max_t", 0),
            final_t=data.get("final_t", 0),
            mode=data.get("mode", "일반"),
            total_buys=data.get("total_buys", 0),
            total_sells=data.get("total_sells", 0),
            reverse_entered=data.get("reverse_entered", False),
            shares_held=data.get("shares_held", 0),
            avg_price=data.get("avg_price", 0),
        )


class SettlementHistory:
    """정산 이력 저장소"""

    FILE = "data/settlement_history.json"

    def __init__(self):
        self.records: List[SettlementRecord] = []
        self._next_cycle_id = 1
        self._load()

    def _load(self):
        if not os.path.exists(self.FILE):
            logger.info("정산 이력 없음, 새로 생성")
            return
        
        try:
            with open(self.FILE, 'r') as f:
                data = json.load(f)
                self.records = [SettlementRecord.from_dict(r) for r in data.get("records", [])]
                self._next_cycle_id = data.get("next_cycle_id", len(self.records) + 1)
                logger.info(f"정산 이력 {len(self.records)}개 로드 완료")
        except Exception as e:
            logger.error(f"정산 이력 로드 실패: {e}")
            self.records = []

    def _save(self):
        os.makedirs("data", exist_ok=True)
        with open(self.FILE, 'w') as f:
            json.dump({
                "records": [r.to_dict() for r in self.records],
                "next_cycle_id": self._next_cycle_id
            }, f, indent=2, default=str)

    def add(self, record: SettlementRecord):
        """정산 기록 추가"""
        # cycle_id 자동 할당
        if record.cycle_id <= 0:
            record.cycle_id = self._next_cycle_id
            self._next_cycle_id += 1
        
        self.records.append(record)
        self._save()
        logger.info(f"정산 기록 저장: #{record.cycle_id}, 수익률 {record.return_pct:.2f}%")

    def get_recent(self, n: int = 5) -> List[SettlementRecord]:
        """최근 n개 조회 (최신 순)"""
        return sorted(self.records, key=lambda r: r.cycle_id, reverse=True)[:n]

    def get_all_summary(self) -> str:
        """전체 요약"""
        if not self.records:
            return "아직 정산 이력이 없습니다."
        
        total_cycles = len(self_records := self.records)
        positive = len([r for r in self.records if r.profit_loss >= 0])
        negative = total_cycles - positive
        
        avg_return = sum(r.return_pct for r in self.records) / total_cycles
        total_profit = sum(r.profit_loss for r in self.records)
        max_return = max(r.return_pct for r in self.records)
        min_return = min(r.return_pct for r in self.records)
        
        return (
            f"📊 전체 정산 요약\n"
            f"총 사이클: {total_cycles}\n"
            f"🟢 수익: {positive}회 | 🔴 손실: {negative}회\n"
            f"평균 수익률: {avg_return:+.2f}%\n"
            f"누적 수익: ${total_profit:+.2f}\n"
            f"최고: {max_return:+.2f}% | 최저: {min_return:+.2f}%"
        )
    
    def get_list_for_buttons(self) -> List[tuple]:
        """버튼용: (cycle_id, label)"""
        recent = self.get_recent(10)
        return [(r.cycle_id, r.format_summary()) for r in recent]

    def find_by_id(self, cycle_id: int) -> Optional[SettlementRecord]:
        for r in self.records:
            if r.cycle_id == cycle_id:
                return r
        return None
