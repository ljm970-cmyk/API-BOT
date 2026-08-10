import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.config_loader import load_config
from utils.logger import setup_logger
from utils.timezone import MarketTime
from models.user_config import UserConfigManager, UserStrategyConfig
from api.client import KiwoomClient
from telegram.keyboards import (
    get_stock_select_keyboard,
    get_split_select_keyboard,
    get_seed_input_guide,
    get_seed_confirm_keyboard,
    get_setup_complete_keyboard,
    get_main_menu_after_setup,
    get_order_confirm_buttons,
)
from telegram.setup_flow import SetupFlow, SetupStep

logger = setup_logger()

# 전역: 사용자 설정 저장소, 대화별 상태
user_configs = UserConfigManager()
pending_plans = {}


class TelegramHandlers:
    def __init__(self):
        config = load_config()
        kiwoom = config["kiwoom"]

        self.client = KiwoomClient(
            app_key=kiwoom["app_key"],
            app_secret=kiwoom["app_secret"],
            base_url=kiwoom["base_url"],
            account_no=kiwoom["account_no"],
            mock=kiwoom.get("mock", False),
        )

        # 사용자별 전략 객체 (설정 후 생성)
        self.strategies = {}

    # ============================================================
    # /start 명령
    # ============================================================
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id

        # 이미 설정 완료?
        config = user_configs.get(chat_id)
        if config:
            await self._show_main_menu(chat_id, update.message.reply_text)
            return

        # 첫 설정 시작
        SetupFlow.set_state(chat_id, SetupStep.SELECT_STOCK)

        welcome = (
            f"🎉 무한매수법 트레이딩 시작\n\n"
            f"투자하실 종목을 선택하세요.\n"
            f"({MarketTime.get_korea_time().strftime('%m/%d %H:%M')} KST)"
        )

        await update.message.reply_text(
            welcome,
            reply_markup=get_stock_select_keyboard(),
        )

    # ============================================================
    # 모든 콜백 버튼 라우팅
    # ============================================================
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        data = query.data
        chat_id = update.effective_chat.id
        logger.info(f"[{chat_id}] 콜백: {data}")

        # 설정 중이면 설정 플로우로
        if SetupFlow.is_setting_up(chat_id):
            await self._handle_setup_callback(chat_id, data, query)
            return

        # 설정 완료 후 메인 메뉴
        await self._handle_main_callback(chat_id, data, query)

    # ============================================================
    # 설정 플로우 (종목 → 분할 → 시드 → 확인)
    # ============================================================
    async def _handle_setup_callback(self, chat_id: int, data: str, query):
        state = SetupFlow.get_state(chat_id)
        current_data = state["data"]

        # --- 종목 선택 ---
        if data.startswith("stock|"):
            stock_code = data.split("|")[1]
            current_data["stock_code"] = stock_code
            SetupFlow.set_state(chat_id, SetupStep.SELECT_SPLIT, current_data)

            name = "TQQQ" if stock_code == "TQQQ" else "SOXL"
            target = "+15%" if stock_code == "TQQQ" else "+20%"

            await query.edit_message_text(
                f"선택: 📈 {name}\n"
                f"목표 수익: {target}\n\n"
                f"분할 수를 선택하세요.\n"
                f"⚡ 20분할: 공격적\n"
                f"🛡️ 40분할: 안정적",
                reply_markup=get_split_select_keyboard(stock_code),
            )
            return

        if data == "stock_help":
            await query.edit_message_text(
                "TQQQ: 나스닥 100지수 3배 레버리지 ETF\n"
                "SOXL: 필라델피아 반도체지수 3배 레버리지 ETF\n\n"
                "둘 중 투자할 종목을 선택하세요.",
                reply_markup=get_stock_select_keyboard(),
            )
            return

        # --- 분할 선택 ---
        if data.startswith("split|"):
            _, stock_code, split_str = data.split("|")
            split_count = int(split_str)

            current_data["stock_code"] = stock_code
            current_data["split_count"] = split_count
            SetupFlow.set_state(chat_id, SetupStep.INPUT_SEED, current_data)

            await query.edit_message_text(
                get_seed_input_guide(stock_code, split_count),
            )
            return

        if data == "back_to_stock":
            SetupFlow.set_state(chat_id, SetupStep.SELECT_STOCK, {})
            await query.edit_message_text(
                "종목을 선택하세요.",
                reply_markup=get_stock_select_keyboard(),
            )
            return

        # --- 최종 확인 ---
        if data.startswith("confirm|"):
            _, stock_code, split_str, seed_str = data.split("|")
            seed = float(seed_str)

            # 설정 저장
            final_config = UserStrategyConfig(
                chat_id=chat_id,
                stock_code=stock_code,
                split_count=int(split_str),
                total_capital=seed,
            )
            user_configs.set(final_config)
            SetupFlow.clear_state(chat_id)

            # 전략 객체 생성
            from strategy.infinite_buy import InfiniteBuyStrategy

            self.strategies[chat_id] = InfiniteBuyStrategy(
                self.client, stock_code, int(split_str), seed
            )

            per_buy = seed / int(split_str)
            await query.edit_message_text(
                f"✅ 설정 완료!\n\n"
                f"{final_config.stock_name} {split_str}분할\n"
                f"시드: ${seed:,.0f}\n"
                f"1회 매수: ${per_buy:,.2f}\n\n"
                f"매일 저녁 5/6시에 리포트가 생성됩니다.",
                reply_markup=get_setup_complete_keyboard(),
            )
            return

        if data == "restart_setup":
            await self._do_restart_setup(chat_id, query)
            return

        # --- 기타 ---
        await query.edit_message_text(
            "알 수 없는 명령입니다.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 메인", callback_data="restart_setup")]]
            ),
        )

    # ============================================================
    # 텍스트 입력 (시드 금액)
    # ============================================================
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        text = update.message.text.strip()

        # 설정 중 시드 입력
        if SetupFlow.is_setting_up(chat_id):
            state = SetupFlow.get_state(chat_id)

            if state["step"] == SetupStep.INPUT_SEED:
                numbers = re.findall(r"[\d,]+", text)
                if not numbers:
                    await update.message.reply_text(
                        "숫자를 입력해주세요. (예: 2000)",
                    )
                    return

                try:
                    seed = float(numbers[0].replace(",", ""))

                    if seed < 1000:
                        await update.message.reply_text(
                            "최소 $1,000 이상 입력해주세요.",
                        )
                        return

                    if seed > 100_000:
                        await update.message.reply_text(
                            "너무 큰 금액입니다. 확인 후 다시 입력해주세요.",
                        )
                        return

                    data = state["data"].copy()
                    data["total_capital"] = seed
                    SetupFlow.set_state(chat_id, SetupStep.CONFIRM, data)

                    summary = SetupFlow.format_summary(data)

                    await update.message.reply_text(
                        summary,
                        reply_markup=get_seed_confirm_keyboard(
                            data["stock_code"], data["split_count"], seed
                        ),
                    )

                except ValueError:
                    await update.message.reply_text("올바른 숫자를 입력해주세요.")
                return

        # 설정 완료 후 일반 메시지
        config = user_configs.get(chat_id)
        if not config:
            await update.message.reply_text(
                "⚠️ 설정이 필요합니다.\n/start를 입력하세요.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🚀 설정 시작", callback_data="restart_setup")]]
                ),
            )
            return

        await update.message.reply_text(
            "메뉴에서 선택하세요.",
            reply_markup=get_main_menu_after_setup(),
        )

    # ============================================================
    # ⭐ 메인 메뉴 콜백 (가드 로직 포함)
    # ============================================================
    async def _handle_main_callback(self, chat_id: int, data: str, query):
        """
        메인 메뉴 처리
        설정 안 된 사용자는 메뉴 진입 불가 (강제 리다이렉트)
        """

        # ========== ⭐ 가드 로직 시작 ==========
        config = user_configs.get(chat_id)
        if not config and data not in ["restart_setup"]:
            await query.edit_message_text(
                "⚠️ 설정이 필요합니다.\n\n"
                "/start를 입력하거나 아래 버튼을 눌러\n"
                "종목, 분할, 시드를 설정하세요.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🚀 설정 시작", callback_data="restart_setup")]]
                ),
            )
            return
        # ========== ⭐ 가드 로직 끝 ==========

        # --- 내 설정 확인 ---
        if data == "my_config":
            per_buy = config.total_capital / config.split_count
            await query.edit_message_text(
                f"⚙️ 내 설정\n\n"
                f"종목: {config.stock_name}\n"
                f"분할: {config.split_count}분할\n"
                f"시드: ${config.total_capital:,.0f}\n"
                f"1회: ${per_buy:,.2f}\n"
                f"목표: {config.target_profit_pct:.0f}%",
                reply_markup=get_main_menu_after_setup(),
            )
            return

        # --- 오늘의 리포트 ---
        if data == "daily_report":
            await self._show_daily_report(chat_id, query)
            return

        # --- 정산 이력 ---
        if data == "settlement_history":
            text = self._get_settlement_text(chat_id)
            await query.edit_message_text(text, reply_markup=get_main_menu_after_setup())
            return

        # --- 설정 변경 ---
        if data == "restart_setup":
            await self._do_restart_setup(chat_id, query)
            return

        # --- 알 수 없는 ---
        await query.edit_message_text(
            "메뉴를 선택하세요.",
            reply_markup=get_main_menu_after_setup(),
        )

    # ============================================================
    # 내부 헬퍼 메서드
    # ============================================================
    async def _show_main_menu(self, chat_id: int, reply_func):
        config = user_configs.get(chat_id)
        name = config.stock_name if config else "?"

        text = (
            f"📊 {name} 무한매수법\n"
            f"(설정 완료)\n\n"
            f"리포트를 확인하세요."
        )
        await reply_func(text, reply_markup=get_main_menu_after_setup())

    async def _show_daily_report(self, chat_id: int, query):
        """오늘의 리포트 생성 및 표시"""
        strategy = self.strategies.get(chat_id)
        config = user_configs.get(chat_id)

        if not strategy:
            if config:
                from strategy.infinite_buy import InfiniteBuyStrategy

                strategy = InfiniteBuyStrategy(
                    self.client,
                    config.stock_code,
                    config.split_count,
                    config.total_capital,
                )
                self.strategies[chat_id] = strategy
            else:
                await query.edit_message_text(
                    "⚠️ 전략 생성 실패. /start로 다시 설정하세요."
                )
                return

        # 현재가 (mock → 실제 API 교체)
        current_price = 73.50  # TODO: strategy.client.get_xxx_price()

        plan = strategy.calculator.create_today_report(
            strategy.position, current_price
        )
        text = plan.format_telegram_report()
        text += f"\n\n({MarketTime.get_korea_time().strftime('%H:%M')})"

        pending_plans[chat_id] = plan

        has_buy = len(plan.loc_buys) + len(plan.crash_buys) > 0
        has_sell = plan.quarter_sell is not None or plan.final_sell is not None

        if not has_buy and not has_sell:
            await query.edit_message_text(
                text + "\n\n오늘은 걸 주문이 없습니다.",
                reply_markup=get_main_menu_after_setup(),
            )
            return

        await query.edit_message_text(text, reply_markup=get_order_confirm_buttons(plan.stock_code))

    def _get_settlement_text(self, chat_id: int) -> str:
        from strategy.settlement_tracker import SettlementTracker

        tracker = getattr(self, "settlement_tracker", None)
        if tracker is None:
            tracker = SettlementTracker()
            self.settlement_tracker = tracker

        return tracker.history.get_all_summary()

    async def _do_restart_setup(self, chat_id: int, query):
        """설정 초기화 후 재시작"""
        user_configs.delete(chat_id)
        self.strategies.pop(chat_id, None)
        SetupFlow.set_state(chat_id, SetupStep.SELECT_STOCK)

        await query.edit_message_text(
            "🔄 새 설정을 시작합니다.\n\n종목을 선택하세요.",
            reply_markup=get_stock_select_keyboard(),
        )
