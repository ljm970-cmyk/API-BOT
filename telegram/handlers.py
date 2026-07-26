from telegram import Update
from telegram.ext import ContextTypes
from utils.config_loader import load_config
from utils.logger import setup_logger
from utils.timezone import MarketTime
from api.client import KiwoomClient
from telegram.keyboards import (
    get_function_menu, get_order_confirm_buttons,
    get_final_result_buttons, get_main_menu_button
)
from strategy.calculator import InfiniteBuyCalculator
from strategy.infinite_buy import InfiniteBuyStrategy
from models.order_plan import DailyOrderPlan, OrderType

logger = setup_logger()

# 보류중인 리포트 저장 (채팅ID -> plan)
pending_plans: dict = {}


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

    # ==================== 시작 ====================

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome = (
            f"키움증권 무한매수법 v4.0\n\n"
            f"리포트 버튼을 눌러 오늘의 매매 계획을 확인하세요.\n"
            f"({MarketTime.get_korea_time().strftime('%m/%d %H:%M')} KST)"
        )
        await update.message.reply_text(welcome, reply_markup=get_function_menu())

    # ==================== 리포트 ====================

    async def show_daily_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """[📊 리포트 보기] 버튼 - 사진과 동일한 리포트 생성"""
        query = update.callback_query
        if query:
            await query.answer()
            chat_id = update.effective_chat.id
        else:
            chat_id = update.effective_chat.id
        
        # 현재가 조회 (API 또는 임시값)
        # 실제로는 API 호출해서 current_price 가져와야 함
        current_price = 73.50  # TODO: 실제 API 호출
        
        # 리포트 생성
        plan = self.strategy.calculator.create_today_report(
            self.strategy.position, current_price
        )
        
        # 리포트 텍스트
        report_text = plan.format_telegram_report()
        
        # 시간 추가
        time_str = MarketTime.get_korea_time().strftime("%H:%M")
        report_text += f"\n\n({time_str})"
        
        # 보류 저장
        pending_plans[chat_id] = plan
        
        # 버튼
        if plan.mode == "사이클 종료":
            await (query.edit_message_text if query else update.message.reply_text)(
                report_text + "\n\n🎉 사이클 종료! 축하합니다.",
                reply_markup=get_final_result_buttons(plan.stock_code)
            )
            return
        
        # 매수/매도 있는지 확인
        has_buy = len(plan.loc_buys) + len(plan.crash_buys) > 0
        has_sell = plan.quarter_sell is not None or plan.final_sell is not None
        
        if not has_buy and not has_sell:
            await (query.edit_message_text if query else update.message.reply_text)(
                report_text + "\n\n오늘은 걸 주문이 없습니다.",
                reply_markup=get_function_menu()
            )
            return
        
        # 리포트 + 승인 버튼
        await (query.edit_message_text if query else update.message.reply_text)(
            report_text,
            reply_markup=get_order_confirm_buttons(plan.stock_code)
        )

    # ==================== 버튼 핸들러 ====================

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        chat_id = update.effective_chat.id
        
        logger.info(f"콜백: {data}")

        # 메인/리포트
        if data == "main_menu":
            await self.start(update, context)
            return
        
        if data == "daily_report":
            await self.show_daily_report(update, context)
            return

        # 매수 승인
        if data.startswith("confirm_buy|"):
            await self._execute_buy(chat_id, query)
            return

        # 매도 승인
        if data.startswith("confirm_sell|"):
            await self._execute_sell(chat_id, query)
            return

        # 전체 취소
        if data.startswith("cancel_all|"):
            pending_plans.pop(chat_id, None)
            await query.edit_message_text(
                "❌ 전체 취소되었습니다.",
                reply_markup=get_function_menu()
            )
            return

    # ==================== 실행 ====================

    async def _execute_buy(self, chat_id: int, query):
        """✅ 매수 승인 처리"""
        plan = pending_plans.get(chat_id)
        if not plan:
            await query.edit_message_text("오류: 리포트를 다시 불러오세요")
            return
        
        # API 호출 (구현 필요)
        executed = []
        failed = []
        
        for o in plan.loc_buys + plan.crash_buys:
            # TODO: 실제 키움 API BUY 호출
            success = True  # mock
            if success:
                executed.append(o.tag)
            else:
                failed.append(o.tag)
        
        # 결과
        result_text = plan.format_execution_result(executed, [])
        if failed:
            result_text += f"\n\n실패: {', '.join(failed)}"
        
        # T값 업데이트 등
        self.strategy.executor.update_after_buy(plan, executed)
        
        await query.edit_message_text(
            result_text,
            reply_markup=get_final_result_buttons(plan.stock_code)
        )

    async def _execute_sell(self, chat_id: int, query):
        """✅ 매도 승인 처리"""
        plan = pending_plans.get(chat_id)
        if not plan:
            await query.edit_message_text("오류: 리포트를 다시 불러오세요")
            return
        
        executed = []
        
        # 쿼터매도 (LOC/MOC)
        if plan.quarter_sell:
            # TODO: 실제 API SELL 호출
            executed.append(plan.quarter_sell.tag)
        
        # 지정가매도
        if plan.final_sell:
            # TODO: 실제 API LIMIT SELL 호출
            executed.append(plan.final_sell.tag)
        
        result_text = plan.format_execution_result([], executed)
        
        # T값 업데이트
        self.strategy.executor.update_after_sell(plan, executed)
        
        await query.edit_message_text(
            result_text,
            reply_markup=get_final_result_buttons(plan.stock_code)
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """텍스트 메시지는 무시하고 메뉴 유도"""
        await update.message.reply_text(
            "버튼을 사용해주세요:",
            reply_markup=get_function_menu()
        )
