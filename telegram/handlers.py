import re
from telegram import Update
from telegram.ext import ContextTypes
from utils.config_loader import load_config
from utils.logger import setup_logger
from utils.timezone import MarketTime
from models.user_config import UserConfigManager, UserStrategyConfig
from api.client import KiwoomClient
from telegram.keyboards import *
from telegram.setup_flow import SetupFlow, SetupStep

logger = setup_logger()

# 사용자 설정 저장소
user_configs = UserConfigManager()
# 보류중인 주문 계획
pending_plans = {}


class TelegramHandlers:
    def __init__(self):
        # 시스템 API 설정 (키움증권 HTS ID 연동)
        config = load_config()
        kiwoom = config["kiwoom"]
        
        self.client = KiwoomClient(
            app_key=kiwoom["app_key"],
            app_secret=kiwoom["app_secret"],
            base_url=kiwoom["base_url"],
            account_no=kiwoom["account_no"],
            mock=kiwoom.get("mock", False)
        )
        
        # 전략은 사용자별로 동적 생성 (초기엔 None)
        self.strategies = {}  # chat_id -> InfiniteBuyStrategy

    # ==================== /start ====================

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        
        # 이미 설정 완료?
        config = user_configs.get(chat_id)
        if config:
            # 기존 설정으로 바로 시작
            await self._show_main_menu(chat_id, update.message.reply_text)
            return
        
        # 첫 시작: 설정 플로우 진입
        SetupFlow.set_state(chat_id, SetupStep.SELECT_STOCK)
        
        welcome = (
            f"🎉 무한매수법 트레이딩 시작\n\n"
            f"투자하실 종목을 선택하세요.\n"
            f"({MarketTime.get_korea_time().strftime('%m/%d %H:%M')} KST)"
        )
        
        await update.message.reply_text(
            welcome,
            reply_markup=get_stock_select_keyboard()
        )

    # ==================== 콜백 전체 라우팅 ====================

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        chat_id = update.effective_chat.id
        logger.info(f"[{chat_id}] 콜백: {data}")
        
        # === 설정 중이면 설정 핸들러로 ===
        if SetupFlow.is_setting_up(chat_id):
            await self._handle_setup_callback(chat_id, data, query)
            return
        
        # === 설정 완료 후 일반 메뉴 ===
        await self._handle_main_callback(chat_id, data, query)

    async def _handle_setup_callback(self, chat_id: int, data: str, query):
        """초기 설정 단계별 처리"""
        state = SetupFlow.get_state(chat_id)
        current_data = state["data"]
        
        # --- 1단계: 종목 선택 ---
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
                f"⚡ 20분할: 공격적, 빠른 회전\n"
                f"🛡️ 40분할: 안정적, 방어적",
                reply_markup=get_split_select_keyboard(stock_code)
            )
            return
        
        if data == "stock_help":
            await query.edit_message_text(
                "TQQQ: 나스닥 100 3배 레버리지 ETF (+15% 목표)\n"
                "SOXL: 반도체 3배 레버리지 ETF (+20% 목표)\n\n"
                "둘 중 하나 선택 후 진행하세요.",
                reply_markup=get_stock_select_keyboard()
            )
            return
        
        # --- 2단계: 분할 선택 ---
        if data.startswith("split|"):
            _, stock_code, split_str = data.split("|")
            split_count = int(split_str)
            
            current_data["stock_code"] = stock_code
            current_data["split_count"] = split_count
            
            SetupFlow.set_state(chat_id, SetupStep.INPUT_SEED, current_data)
            
            await query.edit_message_text(
                get_seed_input_guide(stock_code, split_count),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 분할 다시 선택", callback_data=f"stock|{stock_code}")]
                ])
            )
            return
        
        if data == "back_to_stock":
            SetupFlow.set_state(chat_id, SetupStep.SELECT_STOCK, {})
            await query.edit_message_text(
                "종목을 선택하세요.",
                reply_markup=get_stock_select_keyboard()
            )
            return
        
        # --- 3단계: 확인 (설정 완료 버튼에서) ---
        if data.startswith("confirm|"):
            _, stock_code, split_str, seed_str = data.split("|")
            seed = float(seed_str)
            
            final_config = UserStrategyConfig(
                chat_id=chat_id,
                stock_code=stock_code,
                split_count=int(split_str),
                total_capital=seed
            )
            
            # 저장
            user_configs.set(final_config)
            SetupFlow.clear_state(chat_id)
            
            # 전략 생성
            from strategy.infinite_buy import InfiniteBuyStrategy
            self.strategies[chat_id] = InfiniteBuyStrategy(
                self.client, stock_code, int(split_str), seed
            )
            
            # 완료 메시지
            per_buy = seed / int(split_str)
            await query.edit_message_text(
                f"✅ 설정 완료!\n\n"
                f"{final_config.stock_name} {split_str}분할\n"
                f"시드: ${seed:,.0f}\n"
                f"1회 매수: ${per_buy:,.2f}\n\n"
                f"매일 저녁 5/6시에 리포트가 생성됩니다.",
                reply_markup=get_setup_complete_keyboard()
            )
            return
        
        if data == "restart_setup":
            user_configs.delete(chat_id)
            setup_states.pop(chat_id, None)
            SetupFlow.set_state(chat_id, SetupStep.SELECT_STOCK)
            
            await query.edit_message_text(
                "🔄 새로운 설정을 시작합니다.\n\n종목을 선택하세요.",
                reply_markup=get_stock_select_keyboard()
            )
            return
        
        # 기타
        await query.edit_message_text("알 수 없는 명령입니다.", reply_markup=get_main_menu_button())

    # ==================== 텍스트 입력 (시드 금액) ====================

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        text = update.message.text.strip()
        
        # 설정 중 시드 입력?
        if SetupFlow.is_setting_up(chat_id):
            state = SetupFlow.get_state(chat_id)
            
            if state["step"] == SetupStep.INPUT_SEED:
                # 숫자만 추출
                numbers = re.findall(r'[\d,]+', text)
                if not numbers:
                    await update.message.reply_text(
                        "숫자를 입력해주세요. (예: 2000)",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 다시", callback_data="back_to_stock")]
                        ])
                    )
                    return
                
                try:
                    seed = float(numbers[0].replace(",", ""))
                    
                    if seed < 1000:
                        await update.message.reply_text(
                            "최소 $1,000 이상 입력해주세요.",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("🔙 다시", callback_data="back_to_stock")]
                            ])
                        )
                        return
                    
                    if seed > 100000:
                        await update.message.reply_text(
                            "너무 큰 금액입니다. 확인 후 다시 입력해주세요.",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("🔙 다시", callback_data="back_to_stock")]
                            ])
                        )
                        return
                    
                    # 확인 단계로
                    data = state["data"].copy()
                    data["total_capital"] = seed
                    
                    SetupFlow.set_state(chat_id, SetupStep.CONFIRM, data)
                    
                    # 요약 표시
                    summary = SetupFlow.format_summary(data)
                    
                    await update.message.reply_text(
                        summary,
                        reply_markup=get_seed_confirm_keyboard(
                            data["stock_code"], data["split_count"], seed
                        )
                    )
                    
                except ValueError:
                    await update.message.reply_text(
                        "올바른 숫자를 입력해주세요.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔙 다시", callback_data="back_to_stock")]
                        ])
                    )
                return
        
        # 설정 완료 후 일반 메시지
        await update.message.reply_text(
            "메뉴에서 선택하세요.",
            reply_markup=get_main_menu_after_setup()
        )

    # ==================== 설정 완료 후 메뉴 ====================

    async def _show_main_menu(self, chat_id: int, reply_func):
        """설정 완료 후 메인 메뉴"""
        config = user_configs.get(chat_id)
        name = config.stock_name if config else "?"
        
        text = (
            f"📊 {name} 무한매수법\n"
            f"(설정 완료)\n\n"
            f"리포트를 확인하세요."
        )
        await reply_func(text, reply_markup=get_main_menu_after_setup())

    async def _handle_main_callback(self, chat_id: int, data: str, query):
        """기존 일반 메뉴 처리"""
        
        if data == "my_config":
            config = user_configs.get(chat_id)
            if not config:
                await query.edit_message_text("설정이 없습니다. /start로 다시 설정하세요.")
                return
     
            per_buy = config.total_capital / config.split_count
            await query.edit_message_text(
                f"⚙️ 내 설정\n\n"
                f"종목: {config.stock_name}\n"
                f"분할: {config.split_count}분할\n"
                f"시드: ${config.total_capital:,.0f}\n"
                f"1회: ${per_buy:,.2f}\n"
                f"목표: {config.target_profit_pct:.0f}%",
                reply_markup=get_main_menu_after_setup()
            )
            return
        
        if data == "daily_report":
            await self._show_daily_report(chat_id, query)
            return
        
        if data == "settlement_history":
            # 정산 이력
            await query.edit_message_text("정산 이력 조회 (구현 예정)", reply_markup=get_main_menu_after_setup())
            return
        
        if data == "restart_setup":
            user_configs.delete(chat_id)
            SetupFlow.set_state(chat_id, SetupStep.SELECT_STOCK)
            await query.edit_message_text(
                "🔄 새 설정을 시작합니다.\n\n종목을 선택하세요.",
                reply_markup=get_stock_select_keyboard()
            )
            return

    async def _show_daily_report(self, chat_id: int, query):
        """리포트 표시 (기존 코드와 유사)"""
        # 전략 가져오기/생성
        strategy = self.strategies.get(chat_id)
        if not strategy:
            config = user_configs.get(chat_id)
            if config:
                from strategy.infinite_buy import InfiniteBuyStrategy
                strategy = InfiniteBuyStrategy(
                    self.client, config.stock_code,
                    config.split_count, config.total_capital
                )
                self.strategies[chat_id] = strategy
        
        if not strategy:
            await query.edit_message_text("전략이 없습니다. /start로 설정하세요.")
            return
        
        # 현재가 조회 (API)
        # 현재는 mock
        current_price = 73.50  # 실제: strategy.client.get_price(...)
        
        plan = strategy.calculator.create_today_report(strategy.position, current_price)
        text = plan.format_telegram_report()
        
        # 시간
        kst = MarketTime.get_korea_time().strftime("%H:%M")
        text += f"\n\n({kst})"
        
        # 저장
        pending_plans[chat_id] = plan
        
        has_buy = len(plan.loc_buys) + len(plan.crash_buys) > 0
        has_sell = plan.quarter_sell is not None or plan.final_sell is not None
        
        if not has_buy and not has_sell:
            await query.edit_message_text(
                text + "\n\n오늘은 걸 주문이 없습니다.",
                reply_markup=get_main_menu_after_setup()
            )
            return
        
        await query.edit_message_text(
            text,
            reply_markup=get_order_confirm_buttons(plan.stock_code)
        )
