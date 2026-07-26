from telegram import Update
from telegram.ext import ContextTypes
from utils.config_loader import load_config
from utils.logger import setup_logger
from utils.timezone import MarketTime, OrderTimeFormatter
from api.client import KiwoomClient
from telegram.keyboards import (get_main_menu, get_quantity_keyboard, 
                                get_order_type_keyboard, get_confirm_keyboard, 
                                get_main_back)

logger = setup_logger()

user_states = {}

class TelegramHandlers:
    def __init__(self):
        config = load_config()
        kiwoom_cfg = config["kiwoom"]
        self.client = KiwoomClient(
            app_key=kiwoom_cfg["app_key"],
            app_secret=kiwoom_cfg["app_secret"],
            base_url=kiwoom_cfg["base_url"],
            account_no=kiwoom_cfg["account_no"],
            mock=kiwoom_cfg.get("mock", False)
        )
        
        from strategy.infinite_buy import InfiniteBuyStrategy
        stg_cfg = config["strategy"]
        self.strategy = InfiniteBuyStrategy(
            self.client, stg_cfg["stock_code"], 
            stg_cfg["split_count"], 
            stg_cfg["total_capital"]
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # 시간 정보 표시 [1]
        time_info = OrderTimeFormatter.order_time_info()
        
        welcome = (
            f"키움증권 무한매수법 봇\n\n"
            f"{time_info}\n\n"
            f"⚠️ 지정가매도는 {MarketTime.get_limit_order_deadline_kst()[1]}에 걸어두세요\n\n"
            f"메뉴를 선택하세요:"
        )
        
        if self.strategy.position.is_reverse_mode:
            welcome += "\n\n🔄 현재 리버스모드 진행중!"
        
        await update.message.reply_text(welcome, reply_markup=get_main_menu())

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        chat_id = update.effective_chat.id
        
        if data == "main_menu":
            await self._show_main_menu(query)
            return
        
        if data == "time_info":
            # 시간 정보 요청
            time_info = OrderTimeFormatter.order_time_info()
            hours = MarketTime.get_market_hours_kst()
            
            text = (
                f"{time_info}\n\n"
                f"📅 오늘의 장 운영 시간\n"
                f"현재: {'서머타임' if hours['is_summer_time'] else '비서머타임'}\n"
            )
            
            for k, v in hours.get('schedule', {}).items():
                text += f"{k}: {v}\n"
            
            text += f"\n⏰ LOC 매수/매도: 장 마감 시까지 유효"
            text += f"\n⏰ 지정가 매도: 프리장~애프터까지 유효"
            
            await query.edit_message_text(text, reply_markup=get_main_menu())
            return
            
        if data == "balance":
            await self._show_balance(query)
            return
        
        if data == "positions":
            await self._show_positions(query)
            return
        
        if data == "new_order":
            # 주문 시간 안내 [1]
            limit_deadline = MarketTime.get_limit_order_deadline_kst()
            await query.edit_message_text(
                f"🛒 신규 주문\n\n"
                f"지금 한국 시간: {MarketTime.get_korea_time().strftime('%H:%M')}\n"
                f"지정가매도 걸기 적정 시간: 저녁 {limit_deadline[1]}\n\n"
                f"종목코드 6자리를 입력하세요 (예: 005930)",
                reply_markup=get_main_back()
            )
            user_states[chat_id] = {"step": "waiting_code"}
            return

        # ... 나머지 콜백 처리는 기존과 동일

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        text = update.message.text.strip()
        state = user_states.get(chat_id)
        
        if state and state.get("step") == "waiting_code":
            code = ''.join(c for c in text if c.isdigit())
            if len(code) != 6:
                # 시간 정보와 함께 에러
                time_note = f"\n\n현재 한국 시간: {MarketTime.get_korea_time().strftime('%H:%M')}"
                await update.message.reply_text(
                    f"6자리 종목코드를 입력하세요{time_note}",
                    reply_markup=get_main_back()
                )
                return
            await update.message.reply_text(
                f"{code} 수량 선택:",
                reply_markup=get_quantity_keyboard(code)
            )
            user_states.pop(chat_id, None)
            return

        await update.message.reply_text(
            "메뉴에서 선택하세요",
            reply_markup=get_main_menu()
        )

    async def _show_main_menu(self, query):
        time_info = f"\n🕐 현재: {MarketTime.get_korea_time().strftime('%H:%M')}"
        await query.edit_message_text(f"메인 메뉴{time_info}", reply_markup=get_main_menu())

    async def _show_balance(self, query):
        p = self.strategy.position
        
        # 현재 시간 정보
        is_summer = MarketTime.is_summer_time()
        market_schedule = "서머타임" if is_summer else "비서머타임"
        
        text = (
            f"💰 계좌 상태 ({market_schedule})\n"
            f"조회 시간: {MarketTime.get_korea_time().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"모드: {'리버스' if p.is_reverse_mode else '일반'}\n"
            f"T값: {p.current_t:.4f}\n"
            f"보유: {p.shares_held}주 @ ${p.avg_price:.2f}\n"
            f"잔금: ${p.remaining_capital:.2f}\n\n"
            f"지정가매도 걸기는 저녁 {MarketTime.get_limit_order_deadline_kst()[1]} 권장"
        )
        await query.edit_message_text(text, reply_markup=get_main_menu())

    async def _show_positions(self, query):
        p = self.strategy.position
        mode = "🔄 리버스모드" if p.is_reverse_mode else "📈 일반모드"
        
        time_note = f"\n(현재 한국 시간: {MarketTime.get_korea_time().strftime('%H:%M')})"
        
        text = (
            f"{mode}{time_note}\n\n"
            f"평단: ${p.avg_price:.2f}\n"
            f"보유: {p.shares_held}주"
        )
        await query.edit_message_text(text, reply_markup=get_main_menu())
