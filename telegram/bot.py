from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from utils.config_loader import load_config
from utils.logger import setup_logger
from telegram.handlers import TelegramHandlers

logger = setup_logger()


class KiwoomTelegramBot:
    def __init__(self):
        config = load_config()
        self.token = config["telegram"]["bot_token"]
        self.handlers = TelegramHandlers()

    def run(self):
        logger.info("무적 좀비봇 시작")
        application = Application.builder().token(self.token).build()

        # ⭐ 핵심 명령어 등록
        application.add_handler(CommandHandler("start", self.handlers.start))
        application.add_handler(CommandHandler("update", self.handlers.cmd_update))  # ⭐ NEW

        application.add_handler(CallbackQueryHandler(self.handlers.handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_message))

        logger.info("데몬 폴링 시작...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
