from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List
from utils.timezone import MarketTime

def get_function_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 오늘의 리포트", callback_data="daily_report")],
        [InlineKeyboardButton("📋 정산 이력", callback_data="settlement_history")],
        [InlineKeyboardButton("⚙️ 설정", callback_data="settings")]
    ])

def get_settlement_menu(recent_cycles: List[tuple]):
    """
    정산 이력 목록 + 돌아가기 버튼
    
    recent_cycles: [(cycle_id, label), ...]
    """
    keyboard = []
    for cycle_id, label in recent_cycles:
        keyboard.append([InlineKeyboardButton(label, callback_data=f"settle_detail|{cycle_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 메인 메뉴", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_settlement_detail_buttons(cycle_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 목록으로", callback_data="settlement_history")],
        [InlineKeyboardButton("🏠 메인 메뉴", callback_data="main_menu")]
    ])

# 기존 버튼들 (변경 없음)
def get_order_confirm_buttons(stock_code: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ 매수 승인", callback_data=f"confirm_buy|{stock_code}"),
            InlineKeyboardButton("✅ 매도 승인", callback_data=f"confirm_sell|{stock_code}")
        ],
        [
            InlineKeyboardButton("❌ 전체 취소", callback_data=f"cancel_all|{stock_code}")
        ]
    ])

def get_final_result_buttons(stock_code: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 다음 리포트", callback_data="daily_report")],
        [InlineKeyboardButton("📋 정산 이력", callback_data="settlement_history")],
        [InlineKeyboardButton("🏠 메인", callback_data="main_menu")]
    ])

def get_main_menu_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 메인 메뉴", callback_data="main_menu")]])
