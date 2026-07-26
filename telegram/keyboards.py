from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("💰 예수금 조회", callback_data="balance")],
        [InlineKeyboardButton("📋 보유 종목", callback_data="positions")],
        [InlineKeyboardButton("📜 주문 내역", callback_data="order_history")],
        [InlineKeyboardButton("🛒 신규 주문", callback_data="new_order")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_quantity_keyboard(stock_code: str):
    quantities = [1, 5, 10, 30, 50, 100]
    keyboard = []
    row = []
    for qty in quantities:
        row.append(InlineKeyboardButton(f"{qty}주", callback_data=f"qty|{stock_code}|{qty}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 메인", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_order_type_keyboard(stock_code: str, quantity: int):
    keyboard = [
        [
            InlineKeyboardButton("📈 시장가 매수", callback_data=f"order|{stock_code}|BUY|{quantity}"),
            InlineKeyboardButton("📉 시장가 매도", callback_data=f"order|{stock_code}|SELL|{quantity}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_confirm_keyboard(stock_code: str, side: str, qty: str):
    keyboard = [
        [
            InlineKeyboardButton("✅ 주문 실행", callback_data=f"confirm|{stock_code}|{side}|{qty}"),
            InlineKeyboardButton("❌ 취소", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 메인 메뉴", callback_data="main_menu")]])
