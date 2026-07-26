from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("💰 예수금/상태", callback_data="balance")],
        [InlineKeyboardButton("📋 보유 종목", callback_data="positions")],
        [InlineKeyboardButton("📜 주문 내역", callback_data="order_history")],
        [InlineKeyboardButton("🕐 장 시간 안내", callback_data="time_info")],
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
            InlineKeyboardButton("📈 LOC 매수", callback_data=f"order|{stock_code}|BUY|{quantity}|LOC"),
            InlineKeyboardButton("📉 LOC 매도", callback_data=f"order|{stock_code}|SELL|{quantity}|LOC")
        ],
        [
            InlineKeyboardButton("🎯 지정가 매도", callback_data=f"order|{stock_code}|SELL|{quantity}|LIMIT")
        ],
        [InlineKeyboardButton("🔙 메인", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_confirm_keyboard(stock_code: str, side: str, qty: str, order_type: str = "LOC"):
    from utils.timezone import MarketTime
    
    side_kr = "매수" if side == "BUY" else "매도"
    time_note = ""
    
    if order_type == "LIMIT":
        deadline = MarketTime.get_limit_order_deadline_kst()
        time_note = f"\n⏰ 지정가는 {deadline[1]}에 걸면 효율적"
    
    keyboard = [
        [
            InlineKeyboardButton(f"✅ {order_type} {side_kr} 확정", 
                               callback_data=f"confirm|{stock_code}|{side}|{qty}|{order_type}"),
        ],
        [InlineKeyboardButton("❌ 취소", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard), time_note  # time_note는 메시지에 함께 표시

def get_main_back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 메인 메뉴", callback_data="main_menu")]])
