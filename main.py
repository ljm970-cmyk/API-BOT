#!/usr/bin/env python3
"""
키움증권 무한매수법 트레이딩 시스템
KST(한국 시간) 영구 고정
"""

import os
import sys
import time

# ========== ⭐ KST 강제 고정 (가장 먼저 실행, 다른 import보다 위) ==========
if os.name == 'posix':  # Linux/macOS
    os.environ['TZ'] = 'Asia/Seoul'
    try:
        time.tzset()  # POSIX: 환경변수 변경 즉시 적용
    except AttributeError:
        pass

elif os.name == 'nt':  # Windows
    # Windows timezone 설정
    os.system('tzutil /s "Korea Standard Time"')
    os.environ['TZ'] = 'Asia/Seoul'

# ========== 표준 라이브러리 ==========
import pytz
from datetime import datetime
from pathlib import Path
import argparse

# pytz로 KST, UTC 객체 생성 (나중에 전역 참조용)
KST = pytz.timezone('Asia/Seoul')
UTC = pytz.UTC


def now_kst():
    """현재 한국 시간 (믿을 수 있는 유일한 시간원)"""
    return datetime.now(KST)


def today_kst():
    """오늘 날짜 KST"""
    return now_kst().date()


# ========== 프로젝트 경로 설정 ==========
sys.path.insert(0, str(Path(__file__).parent))


# ========== 프로젝트 import (경로 설정 이후) ==========
from utils.config_loader import load_config
from utils.logger import setup_logger
from telegram.bot import KiwoomTelegramBot

logger = setup_logger()


def run_bot():
    bot = KiwoomTelegramBot()
    bot.run()


def run_standalone():
    from api.client import KiwoomClient
    from strategy.infinite_buy import InfiniteBuyStrategy
    
    config = load_config()
    k = config["kiwoom"]
    s = config["strategy"]
    
    client = KiwoomClient(
        k["app_key"],
        k["app_secret"],
        k["base_url"],
        k["account_no"],
        k.get("mock", False)
    )
    strategy = InfiniteBuyStrategy(
        client,
        s["stock_code"],
        s["split_count"],
        s["total_capital"]
    )
    
    # 오늘 계획 생성
    plan = strategy.generate_today_plan(current_price=0)
    print(plan)


def main():
    parser = argparse.ArgumentParser(description="키움증권 무한매수법 트레이딩 시스템")
    parser.add_argument("--mode", choices=["bot", "standalone"], default="bot")
    args = parser.parse_args()
    
    if args.mode == "bot":
        run_bot()
    else:
        run_standalone()


if __name__ == "__main__":
    main()
