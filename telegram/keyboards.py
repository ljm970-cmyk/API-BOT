from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Tuple
from utils.timezone import MarketTime

def get_function_menu():
    """기능 선택 메뉴 (처음 / 메뉴 버튼용)"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 리포트 보기", callback_data="daily_report")],
        [InlineKeyboardButton("⚙️ 설정", callback_data="settings")]
    ])

def get_order_confirm_buttons(stock_code: str):
    """
    [✅ 매수 승인] [✅ 매도 승인]
    [❌ 전체 취소]
    """
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
    """
    주문 처리 후: 새 리포트 / 메인메뉴
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 다음 리포트", callback_data="daily_report")],
        [InlineKeyboardButton("🏠 메인", callback_data="main_menu")]
    ])

def get_main_menu_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 메인 메뉴", callback_data="main_menu")]
    ])


def get_report_summary_keyboard(stock_code: str):
    """
    리포트 하단에 표시할 '수정' 버튼 등 (선택)
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 자동 리포트 재생성", callback_data="daily_report")]
    ])
