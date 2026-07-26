from telegram import Update
from telegram.ext import ContextTypes
from utils.config_loader import load_config
from utils.logger import setup_logger
from utils.timezone import MarketTime
from api.client import KiwoomClient
from telegram.keyboards import (
    get_function_menu, get_order_confirm_buttons, get_final_result_buttons,
    get_settlement_menu, get_settlement_detail_buttons, get_main_menu_button
)
from strategy.infinite_buy import InfiniteBuyStrategy

logger = setup_logger()

pending_plans = {}


class TelegramHandlers:
    def __init__(self):
        config = load_config()
        k = config["kiwoom"]
        self.client = KiwoomClient(
            app_key=k["app_key"], app_secret=k["app_secret"],
            base_url=k["base_url"], account_no=k["account_no"],
            mock=k.get("mock", False)
        )
        s = config["strategy"]
        self.strategy = InfiniteBuyStrategy(
            self.client, s["stock_code"], s["split_count"], s["total_capital"]
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # ⭐ 현재 정산 요약 노출
        summary = self.strategy.settlement_tracker.get_summary_text()
        total_msg = (
            f"키움증권 무한매수법 v4.0\n\n"
            f"{summary}\n\n"
            f"현재: {MarketTime.get_korea_time().strftime('%m/%d %H:%M')} KST"
        )
        await update.message.reply_text(total_msg, reply_markup=get_function_menu())

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        chat_id = update.effective_chat.id
        logger.info(f"콜백: {data}")

        # === 메인 ===
        if data == "main_menu":
            await self.start(update, context)
            return

        # === 오늘의 리포트 ===
        if data == "daily_report":
            await self.show_daily_report(update, context)
            return

        # === ⭐ 정산 이력 ===
        if data == "settlement_history":
            await self.show_settlement_history(update, context)
            return

        if data.startswith("settle_detail|"):
            cycle_id = int(data.split("|")[1])
            await self.show_settlement_detail(update, context, cycle_id)
            return

        # === 기존 주문 핸들러들 ===
        if data.startswith("confirm_buy|"):
            await self._execute_buy(chat_id, query)
            return

        if data.startswith("confirm_sell|"):
            await self._execute_sell(chat_id, query)
            return

        if data.startswith("cancel_all|"):
            pending_plans.pop(chat_id, None)
            await query.edit_message_text("❌ 전체 취소", reply_markup=get_function_menu())
            return

    # ==================== ⭐ 정산 이력 조회 ====================

    async def show_settlement_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """정산 이력 목록"""
        query = update.callback_query
        
        # 전체 요약
        summary = self.strategy.settlement_tracker.get_summary_text()
        
        # 최근 목록 버튼
        recent = self.strategy.settlement_tracker.history.get_list_for_buttons()
        
        if not recent:
            text = f"{summary}\n\n📝 아직 완료된 정산이 없습니다."
            await query.edit_message_text(text, reply_markup=get_function_menu())
            return
        
        text = f"{summary}\n\n최근 {len(recent)}개 사이클:"
        for _, label in recent:
            text += f"\n{label}"
        
        await query.edit_message_text(
            text,
            reply_markup=get_settlement_menu(recent)
        )

    async def show_settlement_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE, cycle_id: int):
        """개별 정산 상세"""
        query = update.callback_query
        
        record = self.strategy.settlement_tracker.history.find_by_id(cycle_id)
        if not record:
            await query.edit_message_text("정산 기록을 찾을 수 없습니다.", reply_markup=get_settlement_detail_buttons(0))
            return
        
        text = record.format_telegram_detail()
        
        await query.edit_message_text(
            text,
            reply_markup=get_settlement_detail_buttons(cycle_id)
        )

    # ==================== 기존 메서드들 (생략) ====================
    async def show_daily_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # 기존 코드...
        pass

    async def _execute_buy(self, chat_id: int, query):
        # 기존 코드 + 정산 체크 추가
        # plan = pending_plans.get(chat_id)
        # ... 실행 ...
        # self.strategy.update_after_execution(plan, executed, [])
        pass

    async def _execute_sell(self, chat_id: int, query):
        # 기존 코드 + 정산 체크 추가
        pass
