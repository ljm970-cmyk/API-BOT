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
        logger.info("텔레그램 봇 시작")
        application = Application.builder().token(self.token).build()

        application.add_handler(CommandHandler("start", self.handlers.start))
        application.add_handler(CallbackQueryHandler(self.handlers.handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_message))

        application.run_polling(allowed_updates=Update.ALL_TYPES)

from telegram import Update
