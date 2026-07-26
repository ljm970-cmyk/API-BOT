#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

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
    
    client = KiwoomClient(k["app_key"], k["app_secret"], k["base_url"], k["account_no"], k.get("mock", False))
    strategy = InfiniteBuyStrategy(client, s["stock_code"], s["split_count"], s["total_capital"])
    
    # 오늘 계획 생성
    plan = strategy.generate_today_plan(current_price=0)
    print(plan)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["bot", "standalone"], default="bot")
    args = parser.parse_args()
    
    if args.mode == "bot":
        run_bot()
    else:
        run_standalone()

if __name__ == "__main__":
    main()
