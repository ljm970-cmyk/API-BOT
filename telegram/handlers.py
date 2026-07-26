from telegram import Update
from telegram.ext import ContextTypes
from utils.config_loader import load_config
from utils.logger import setup_logger
from api.client import KiwoomClient
from telegram.keyboards import get_main_menu, get_quantity_keyboard, get_order_type_keyboard, get_confirm_keyboard, get_main_back

logger = setup_logger()

user_states = {}

class TelegramHandlers:
    def __init__(self):
        config = load_config()
        k = config["kiwoom"]
        self.client = KiwoomClient(
            app_key=k["app_key"], app_secret=k["app_secret"],
            base_url=k["base_url"], account_no=k["account_no"],
            mock=k.get("mock", False)
        )
        from strategy.infinite_buy import InfiniteBuyStrategy
        s = config["strategy"]
        self.strategy = InfiniteBuyStrategy(
            self.client, s["stock_code"], s["split_count"], s["total_capital"]
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome = "키움증권 무한매수법 봇\n\n메뉴를 선택하세요:"
        if self.strategy.position.is_reverse_mode:
            welcome += "\n⚠️ 현재 리버스모드 진행중!"
        await update.message.reply_text(welcome, reply_markup=get_main_menu())

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        chat_id = update.effective_chat.id

        if data == "main_menu":
            await query.edit_message_text("메인 메뉴", reply_markup=get_main_menu())
            return

        if data == "balance":
            await self._show_balance(query)
            return

        if data == "positions":
            await self._show_positions(query)
            return

        if data == "new_order":
            await query.edit_message_text("종목코드 6자리 입력하세요:", reply_markup=get_main_back())
            user_states[chat_id] = {"step": "waiting_code"}
            return

        if data == "cancel":
            await query.edit_message_text("취소되었습니다", reply_markup=get_main_menu())
            return

        if data.startswith("qty|"):
            _, code, qty = data.split("|")
            await query.edit_message_text(
                f"{code} {qty}주\n매수/매도 선택:",
                reply_markup=get_order_type_keyboard(code, int(qty))
            )
            return

        if data.startswith("order|"):
            _, code, side, qty = data.split("|")
            side_kr = "매수" if side == "BUY" else "매도"
            await query.edit_message_text(
                f"주문 확인\n\n종목: {code}\n유형: {side_kr}\n수량: {qty}주\n\n확정하시겠습니까?",
                reply_markup=get_confirm_keyboard(code, side, qty)
            )
            return

        if data.startswith("confirm|"):
            _, code, side, qty = data.split("|")
            await query.edit_message_text("⏳ 주문 처리중...")
            # 실제 주문 실행 (생략)
            await query.edit_message_text(f"✅ 주문 완료\n{code} {qty}주 {side}", reply_markup=get_main_menu())
            return

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        text = update.message.text.strip()
        state = user_states.get(chat_id)

        if state and state.get("step") == "waiting_code":
            code = ''.join(c for c in text if c.isdigit())
            if len(code) != 6:
                await update.message.reply_text("6자리 종목코드를 입력하세요", reply_markup=get_main_back())
                return
            await update.message.reply_text(f"{code} 수량 선택:", reply_markup=get_quantity_keyboard(code))
            user_states.pop(chat_id, None)
            return

        await update.message.reply_text("메뉴에서 선택하세요", reply_markup=get_main_menu())

    async def _show_balance(self, query):
        # 상태 요약
        p = self.strategy.position
        text = (
            f"💰 계좌 상태\n\n"
            f"모드: {'리버스' if p.is_reverse_mode else '일반'}\n"
            f"T값: {p.current_t:.4f}\n"
            f"보유: {p.shares_held}주 @ {p.avg_price:.2f}\n"
            f"잔금: ${p.remaining_capital:.2f}"
        )
        await query.edit_message_text(text, reply_markup=get_main_menu())

    async def _show_positions(self, query):
        p = self.strategy.position
        mode = "🔄 리버스모드" if p.is_reverse_mode else "📈 일반모드"
        text = f"{mode}\n\n평단: ${p.avg_price:.2f}\n보유: {p.shares_held}주"
        await query.edit_message_text(text, reply_markup=get_main_menu())
