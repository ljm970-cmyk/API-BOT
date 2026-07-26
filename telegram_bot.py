#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from telegram.bot import KiwoomTelegramBot

if __name__ == "__main__":
    bot = KiwoomTelegramBot()
    bot.run()
