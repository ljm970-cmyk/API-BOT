#!/usr/bin/env python3
"""
헬스체크 + 좀비 복구 에이전트
systemd timer 또는 cron으로 1분마다 실행
"""

import subprocess
import sys
import os
import time

# 상대 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
HEALTH_FILE = os.path.join(PROJECT_DIR, "data", ".bot_health")
SERVICE_NAME = os.environ.get("daemon_name", "kiwoom-infinite-bot")


def is_bot_running():
    """프로세스 확인"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"python3.*telegram_bot"],
            capture_output=True, text=True
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False


def is_healthy():
    """건강 파일 체크"""
    if not os.path.exists(HEALTH_FILE):
        return False
    mtime = os.path.getmtime(HEALTH_FILE)
    return (time.time() - mtime) < 180  # 3분


def restart_bot():
    """재시작"""
    subprocess.run(
        ["sudo", "systemctl", "restart", SERVICE_NAME],
        capture_output=True
    )


def write_health():
    """봇이 직접 호출 (살아있음 표시)"""
    os.makedirs(os.path.dirname(HEALTH_FILE), exist_ok=True)
    with open(HEALTH_FILE, "w") as f:
        f.write(str(int(time.time())))


def main():
    running = is_bot_running()
    healthy = is_healthy() if running else False

    if not running or not healthy:
        print(f"⚠️ Bot unhealthy (running={running}, healthy={healthy})")
        restart_bot()
        return 1

    print("✅ Bot healthy")
    return 0


if __name__ == "__main__":
    # 봇에서 호출: python health_check.py --heartbeat
    if "--heartbeat" in sys.argv:
        write_health()
        print("💓 heartbeat written")
        sys.exit(0)

    sys.exit(main())
