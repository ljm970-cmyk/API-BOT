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
        self.strategies = {}

        # ⭐ 관리자 ID 설정
        self.admin_chat_ids = config["telegram"].get("admin_chat_ids", [])
        
        # ⭐ systemd에서 주입한 daemon_name 읽기 (없으면 기본값)
        self.daemon_name = os.environ.get("daemon_name", "kiwoom-infinite-bot")

    # ============================================================
    # /start
    # ============================================================
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
        await update.message.reply_text(
            welcome,
            reply_markup=get_stock_select_keyboard(),
        )

    # ============================================================
    # ⭐ /update: 깃허브 최신 코드 풀링 + 자가 재시작
    # ============================================================
    async def cmd_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                capture_output=True,
                text=True,
                timeout=60,
                cwd="/home/ubuntu/kiwoom-infinite-buy",
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
            result_restart = subprocess.run(
                ["sudo", "systemctl", "restart", self.daemon_name],
                capture_output=True,
                text=True,
                timeout=30,
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

    # ============================================================
    # 콜백 라우팅
    # ============================================================
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

    # ============================================================
    # 설정 플로우
    # ============================================================
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
                f"선택: 📈 {name}\n"
                f"목표 수익: {target}\n\n"
                f"분할 수를 선택하세요.",
                reply_markup=get_split_select_keyboard(stock_code),
            )
            return

        if data.startswith("split|"):
            _, stock_code, split_str = data.split("|")
            split_count = int(split_str)

            current_data["stock_code"] = stock_code
            current_data["split_count"] = split_count
            SetupFlow.set_state(chat_id, SetupStep.INPUT_SEED, current_data)

            await query.edit_message_text(
                get_seed_input_guide(stock_code, split_count)
            )
            return

        if data.startswith("confirm|"):
            _, stock_code, split_str, seed_str = data.split("|")
            seed = float(seed_str)

            final_config = UserStrategyConfig(
                chat_id=chat_id,
                stock_code=stock_code,
                split_count=int(split_str),
                total_capital=seed,
            )
            user_configs.set(final_config)
            SetupFlow.clear_state(chat_id)

            from strategy.infinite_buy import InfiniteBuyStrategy

            self.strategies[chat_id] = InfiniteBuyStrategy(
                self.client, stock_code, int(split_str), seed
            )

            per_buy = seed / int(split_str)
            await query.edit_message_text(
                f"✅ 설정 완료!\n\n"
                f"{final_config.stock_name} {split_str}분할\n"
                f"시드: ${seed:,.0f}\n"
                f"1회
