import os
import subprocess
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.config_loader import load_config
from utils.logger import setup_logger
from utils.timezone import MarketTime
from models.user_config import UserConfigManager, UserStrategyConfig
from api.client import KiwoomClient
from telegram.keyboards import *
from telegram.setup_flow import SetupFlow, SetupStep

logger = setup_logger()

user_configs = UserConfigManager()
pending_plans = {}


class TelegramHandlers:
    def __init__(self):
        config = load_config()
        kiwoom = config["kiwoom"]

        self.client = KiwoomClient(
            app_key=kiwoom["app_key"], app_secret=kiwoom["app_secret"],
            base_url=kiwoom["base_url"], account_no=kiwoom["account_no"],
            mock=kiwoom.get("mock", False),
        )
        self.strategies = {}

        # ⭐ 관리자 ID 설정
        self.admin_chat_ids = config["telegram"].get("admin_chat_ids", [])
        # ⭐ systemd에서 주입한 daemon_name 읽기 (없으면 기본값)
        self.daemon_name = os.environ.get("daemon_name", "kiwoom-infinite-bot")

    # ==================== /start ====================

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        config = user_configs.get(chat_id)
        if config:
            await self._show_main_menu(chat_id, update.message.reply_text)
            return

        SetupFlow.set_state(chat_id, SetupStep.SELECT_STOCK)
        welcome = (
            f"🎉 무한매수법 트레이딩 시작\n\n"
            f"투자하실 종목을 선택하세요.\n"
            f"({MarketTime.get_korea_now_str()})"
        )
        await update.message.reply_text(welcome, reply_markup=get_stock_select_keyboard())

    # ==================== ⭐ /update 커맨드 ====================

    async def cmd_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /update: 깃허브 최신 코드 풀링 + 자가 재시작
        
        관리자만 사용 가능
        """
        chat_id = update.effective_chat.id

        # 관리자 권한 체크
        if self.admin_chat_ids and chat_id not in self.admin_chat_ids:
            await update.message.reply_text("⛔ 관리자만 사용 가능합니다.")
            return

        await update.message.reply_text("🔄 업데이트 시작...\nGit Pull → 재시작")

        try:
            # 1. git pull
            result_pull = subprocess.run(
                ["git", "pull", "origin", "main"],
                capture_output=True, text=True, timeout=60, cwd="/home/ubuntu/kiwoom-infinite-buy"
            )
            pull_output = result_pull.stdout + result_pull.stderr

            if result_pull.returncode != 0:
                await update.message.reply_text(
                    f"❌ Git Pull 실패:\n{pull_output[:500]}"
                )
                return

            # 성공 로그
            await update.message.reply_text(
                f"✅ Git Pull 완료:\n{pull_output[:300]}\n\n"
                f"🔥 데몬 '{self.daemon_name}' 재시작 중..."
            )

            # 2. systemd 자가 재시작
            # daemon_name을 환경변수에서 읽어옴 (Isolation Leak 방지)
            result_restart = subprocess.run(
                ["sudo", "systemctl", "restart", self.daemon_name],
                capture_output=True, text=True, timeout=30
            )

            if result_restart.returncode != 0:
                await update.message.reply_text(
                    f"⚠️ 재시작 명령 실패:\n"
                    f"{result_restart.stderr[:300]}\n\n"
                    f"수동 실행: sudo systemctl restart {self.daemon_name}"
                )
                return

            # 이 메시지는 재시작 전에 보내짐 (봇이 죽기 전)
            await update.message.reply_text(
                f"🚀 재시작 명령 전송 완료!\n"
                f"데몬: {self.daemon_name}\n"
                f"봇이 새 코드로 부활합니다..."
            )

        except Exception as e:
            logger.exception("Update failed")
            await update.message.reply_text(f"❌ 업데이트 오류: {str(e)}")

    # ==================== 기존 handle_callback ====================

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        data = query.data
        chat_id = update.effective_chat.id
        logger.info(f"[{chat_id}] 콜백: {data}")

        if SetupFlow.is_setting_up(chat_id):
            await self._handle_setup_callback(chat_id, data, query)
            return

        await self._handle_main_callback(chat_id, data, query)

    # ==================== 설정 플로우 (기존 그대로) ====================

    async def _handle_setup_callback(self, chat_id: int, data: str, query):
        state = SetupFlow.get_state(chat_id)
        current_data = state["data"]

        if data.startswith("stock|"):
            stock_code = data.split("|")[1]
            current_data["stock_code"] = stock_code
            SetupFlow.set_state(chat_id, SetupStep.SELECT_SPLIT, current_data)
            name = "TQQQ" if stock_code == "TQQQ" else "SOXL"
            target = "+15%" if stock_code == "TQQQ" else "+20%"
            await query.edit_message_text(
                f"선택: 📈 {name}\n목표 수익: {target}\n\n분할 수를 선택하세요.",
                reply_markup=get_split_select_keyboard(stock_code),
            )
            return

        if data.startswith("split|"):
            _, stock_code, split_str = data.split("|")
            split_count = int(split_str)
            current_data["stock_code"] = stock_code
            current_data["split_count"] = split_count
            SetupFlow.set_state(chat_id, SetupStep.INPUT_SEED, current_data)
            await query.edit_message_text(get_seed_input_guide(stock_code, split_count))
            return

        if data.startswith("confirm|"):
            _, stock_code, split_str, seed_str = data.split("|")
            seed = float(seed_str)

            final_config = UserStrategyConfig(
                chat_id=chat_id, stock_code=stock_code,
                split_count=int(split_str), total_capital=seed,
            )
            user_configs.set(final_config)
            SetupFlow.clear_state(chat_id)

            from strategy.infinite_buy import InfiniteBuyStrategy
            self.strategies[chat_id] = InfiniteBuyStrategy(
                self.client, stock_code, int(split_str), seed
            )

            per_buy = seed / int(split_str)
            await query.edit_message_text(
                f"✅ 설정 완료!\n\n{final_config.stock_name} {split_str}분할\n"
                f"시드: ${seed:,.0f}\n1회 매수: ${per_buy:,.2f}\n\n"
                f"매일 저녁 5/6시에 리포트가 생성됩니다.",
                reply_markup=get_setup_complete_keyboard(),
            )
            return

        if data == "restart_setup":
            await self._do_restart_setup(chat_id, query)
            return

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        text = update.message.text.strip()

        if SetupFlow.is_setting_up(chat_id):
            state = SetupFlow.get_state(chat_id)
            if state["step"] == SetupStep.INPUT_SEED:
                numbers = re.findall(r"[\d,]+", text)
                if not numbers:
                    await update.message.reply_text("숫자를 입력해주세요. (예: 2000)")
                    return
                try:
                    seed = float(numbers[0].replace(",", ""))
                    if seed < 1000:
                        await update.message.reply_text("최소 $1,000 이상 입력해주세요.")
                        return
                    if seed > 100_000:
                        await update.message.reply_text("너무 큰 금액입니다. 확인 후 다시 입력해주세요.")
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

        config = user_configs.get(chat_id)
        if not config:
            await update.message.reply_text(
                "⚠️ 설정이 필요합니다.\n/start를 입력하세요.",
            )
            return
        await update.message.reply_text("메뉴에서 선택하세요.", reply_markup=get_main_menu_after_setup())

    # ==================== 메인 콜백 + ⭐ 가드 로직 ====================

    async def _handle_main_callback(self, chat_id: int, data: str, query):
        config = user_configs.get(chat_id)
        if not config and data not in ["restart_setup"]:
            await query.edit_message_text(
                "⚠️ 설정이 필요합니다.\n\n/start를 입력하거나 아래 버튼을 눌러 설정하세요.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 설정 시작", callback_data="restart_setup")]
                ]),
            )
            return

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

        if data == "daily_report":
            await self._show_daily_report(chat_id, query)
            return

        if data == "settlement_history":
            text = self._get_settlement_text(chat_id)
            await query.edit_message_text(text, reply_markup=get_main_menu_after_setup())
            return

        if data == "restart_setup":
            await self._do_restart_setup(chat_id, query)
            return

    async def _show_main_menu(self, chat_id: int, reply_func):
        config = user_configs.get(chat_id)
        name = config.stock_name if config else "?"
        await reply_func(f"📊 {name} 무한매수법\n(설정 완료)\n\n리포트를 확인하세요.", reply_markup=get_main_menu_after_setup())

    async def _show_daily_report(self, chat_id: int, query):
        strategy = self.strategies.get(chat_id)
        config = user_configs.get(chat_id)
        if not strategy and config:
            from strategy.infinite_buy import InfiniteBuyStrategy
            strategy = InfiniteBuyStrategy(self.client, config.stock_code, config.split_count, config.total_capital)
            self.strategies[chat_id] = strategy
        if not strategy:
            await query.edit_message_text("⚠️ 전략 생성 실패. /start로 다시 설정하세요.")
            return

        current_price = 73.50  # TODO: 실제 API
        plan = strategy.calculator.create_today_report(strategy.position, current_price)
        text = plan.format_telegram_report()
        text += f"\n\n({MarketTime.get_korea_now_str()})"

        pending_plans[chat_id] = plan

        has_buy = len(plan.loc_buys) + len(plan.crash_buys) > 0
        has_sell = plan.quarter_sell is not None or plan.final_sell is not None

        if not has_buy and not has_sell:
            await query.edit_message_text(text + "\n\n오늘은 걸 주문이 없습니다.", reply_markup=get_main_menu_after_setup())
            return

        await query.edit_message_text(text, reply_markup=get_order_confirm_buttons(plan.stock_code))

    def _get_settlement_text(self, chat_id: int) -> str:
        return "정산 이력 (구현 중)"  # TODO

    async def _do_restart_setup(self, chat_id: int, query):
        user_configs.delete(chat_id)
        self.strategies.pop(chat_id, None)
        SetupFlow.set_state(chat_id, SetupStep.SELECT_STOCK)
        await query.edit_message_text("🔄 새 설정을 시작합니다.\n\n종목을 선택하세요.", reply_markup=get_stock_select_keyboard())
