from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List

# ==================== 시작 설정용 키보드 ====================

def get_stock_select_keyboard():
    """종목 선택: TQQQ / SOXL"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📈 TQQQ (나스닥 3x)", callback_data="stock|TQQQ"),
            InlineKeyboardButton("🔥 SOXL (반도체 3x)", callback_data="stock|SOXL")
        ],
        [InlineKeyboardButton("❓ 차이가 뭐예요?", callback_data="stock_help")]
    ])

def get_split_select_keyboard(stock_code: str):
    """분할수 선택: 20 or 40"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ 20분할 (공격적)", callback_data=f"split|{stock_code}|20"),
            InlineKeyboardButton("🛡️ 40분할 (안정적)", callback_data=f"split|{stock_code}|40")
        ],
        [InlineKeyboardButton("🔙 종목 다시 선택", callback_data="back_to_stock")]
    ])

def get_seed_input_guide(stock_code: str, split: int):
    """시드 금액 입력 안내 (텍스트만, 키보드 없음)"""
    name = "TQQQ" if "TQQQ" in stock_code else "SOXL"
    
    per_buy_1k = 1000 / split
    per_buy_2k = 2000 / split
    per_buy_5k = 5000 / split
    per_buy_10k = 10000 / split
    
    return (
        f"💰 {name} {split}분할 시드 설정\n\n"
        f"무한매수법 시작 원금(달러)을 입력하세요.\n"
        f"예시:\n"
        f"  $1,000 → 1회 ${per_buy_1k:.0f}\n"
        f"  $2,000 → 1회 ${per_buy_2k:.0f}\n"
        f"  $5,000 → 1회 ${per_buy_5k:.0f}\n"
        f"  $10,000 → 1회 ${per_buy_10k:.0f}\n\n"
        f"숫자만 입력 (예: 2000)"
    )

def get_seed_confirm_keyboard(stock_code: str, split: int, seed: float):
    """최종 확인 버튼"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ 확인 - 시작!", callback_data=f"confirm|{stock_code}|{split}|{seed}")],
        [InlineKeyboardButton("🔢 금액 다시 입력", callback_data=f"reseed|{stock_code}|{split}")],
        [InlineKeyboardButton("🔙 처음부터 다시", callback_data="restart_setup")]
    ])

def get_setup_complete_keyboard():
    """설정 완료 후"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 오늘의 리포트 보기", callback_data="daily_report")],
        [InlineKeyboardButton("⚙️ 설정 변경", callback_data="restart_setup")]
    ])


# ==================== 기존 메뉴 (설정 완료 후) ====================

def get_main_menu_after_setup():
    """일일 메뉴"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 오늘의 리포트", callback_data="daily_report")],
        [InlineKeyboardButton("📋 내 설정 확인", callback_data="my_config")],
        [InlineKeyboardButton("📈 정산 이력", callback_data="settlement_history")],
        [InlineKeyboardButton("⚙️ 설정 변경", callback_data="restart_setup")]
    ])
