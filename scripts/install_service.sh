#!/bin/bash
# ============================================
# 무적 좀비 봇 systemd 설치 스크립트
# ============================================

set -e

BOT_NAME="kiwoom-infinite-bot"
SERVICE_FILE="/etc/systemd/system/${BOT_NAME}.service"
SUDOERS_FILE="/etc/sudoers.d/99-${BOT_NAME}"

# 현재 사용자/경로 자동 감지
USERNAME=${SUDO_USER:-$(whoami)}
PROJECT_DIR=$(cd "$(dirname "$0")/.."; pwd)

echo "🔧 Zombie Bot Installation"
echo "============================"
echo "User: ${USERNAME}"
echo "Project: ${PROJECT_DIR}"
echo "Service: ${BOT_NAME}"
echo ""

# 확인
read -p "계속하시겠습니까? (y/N) " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "취소됨"
    exit 0
fi

# 1. 서비스 파일 생성
echo "📝 Creating systemd service..."
sudo tee "${SERVICE_FILE}" > /dev/null <<EOF
[Unit]
Description=Trading Zombie Bot Daemon (${BOT_NAME})
After=network.target

[Service]
Type=simple
User=${USERNAME}
Group=${USERNAME}
WorkingDirectory=${PROJECT_DIR}
Environment="TZ=Asia/Seoul"
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONUTF8=1"
Environment="daemon_name=${BOT_NAME}"
ExecStart=${PROJECT_DIR}/.venv/bin/python3 -m telegram_bot
StandardOutput=journal
StandardError=journal
Restart=always
RestartSec=5
StartLimitInterval=60s
StartLimitBurst=5

[Install]
WantedBy=multi-user.target
EOF

# 2. sudoers 설정 (systemctl restart 권한)
echo "⚡ Configuring sudoers..."
sudo tee "${SUDOERS_FILE}" > /dev/null <<EOF
${USERNAME} ALL=(ALL) NOPASSWD: /bin/systemctl restart ${BOT_NAME}
${USERNAME} ALL=(ALL) NOPASSWD: /bin/systemctl daemon-reload
EOF
sudo chmod 440 "${SUDOERS_FILE}"

# 3. systemd 적용
echo "🔄 Reloading daemon..."
sudo systemctl daemon-reload
sudo systemctl enable "${BOT_NAME}"

echo ""
echo "✅ Installation complete!"
echo ""
echo "Commands:"
echo "  sudo systemctl start ${BOT_NAME}     # 시작"
echo "  sudo systemctl stop ${BOT_NAME}      # 중지"
echo "  sudo systemctl restart ${BOT_NAME}     # 재시작"
echo "  sudo systemctl status ${BOT_NAME}    # 상태"
echo "  sudo journalctl -u ${BOT_NAME} -f      # 로그 실시간"
