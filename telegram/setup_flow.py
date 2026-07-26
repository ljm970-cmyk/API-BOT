from enum import Enum, auto
from typing import Dict, Optional
from models.user_config import UserStrategyConfig
from telegram.keyboards import (
    get_stock_select_keyboard,
    get_split_select_keyboard,
    get_seed_confirm_keyboard,
    get_main_menu_after_setup
)

class SetupStep(Enum):
    """초기 설정 단계"""
    IDLE = auto()           # 설정 완료 or 미시작
    SELECT_STOCK = auto()   # 종목 선택 중
    SELECT_SPLIT = auto()   # 분할수 선택 중
    INPUT_SEED = auto()     # 시드 금액 입력 중
    CONFIRM = auto()        # 최종 확인 중

# 사용자별 설정 상태 저장
setup_states: Dict[int, dict] = {}

class SetupFlow:
    """
    텔레그램 초기 설정 흐름 관리
    
    /start → 종목선택 → 분할선택 → 시드입력 → 확인 → 완료
    """

    @classmethod
    def get_state(cls, chat_id: int) -> dict:
        return setup_states.get(chat_id, {"step": SetupStep.IDLE, "data": {}})
    
    @classmethod
    def set_state(cls, chat_id: int, step: SetupStep, data: dict = None):
        setup_states[chat_id] = {"step": step, "data": data or {}}
    
    @classmethod
    def clear_state(cls, chat_id: int):
        setup_states.pop(chat_id, None)
    
    @classmethod
    def is_setting_up(cls, chat_id: int) -> bool:
        state = cls.get_state(chat_id)
        return state["step"] != SetupStep.IDLE
    
    @classmethod
    def format_summary(cls, data: dict) -> str:
        """설정 요약 화면"""
        stock = data.get("stock_code", "?")
        split = data.get("split_count", 0)
        seed = data.get("total_capital", 0)
        per_buy = seed / split if split > 0 else 0
        
        name = "TQQQ" if stock == "TQQQ" else "SOXL"
        target = "15%" if stock == "TQQQ" else "20%"
        
        return (
            f"📋 설정 확인\n\n"
            f"종목: {name} ({stock})\n"
            f"분할: {split}분할\n"
            f"시드: ${seed:,.0f}\n"
            f"1회 매수: ${per_buy:,.2f}\n"
            f"목표 수익: {target}\n\n"
            f"이 설정으로 시작할까요?"
        )
