#!/usr/bin/env python3
"""
텔레그램 봇 실행 파일
KST 영구 고정
"""

import os
import time

# ========== ⭐ KST 강제 고정 ==========
os.environ['TZ'] = 'Asia/Seoul'
try:
    time.tzset()
except AttributeError:
    pass

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from telegram.bot import KiwoomTelegramBot

if __name__ == "__main__":
    bot = KiwoomTelegramBot()
    bot.run()
