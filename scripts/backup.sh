#!/bin/bash
# ============================================
# 데이터 자동 백업
# cron: 0 0 * * * /home/ubuntu/kiwoom-infinite-buy/scripts/backup.sh
# ============================================

PROJECT_DIR=$(cd "$(dirname "$0")/.."; pwd)
BACKUP_DIR="${PROJECT_DIR}/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${DATE}.tar.gz"

mkdir -p "${BACKUP_DIR}"

# 백업 대상
tar -czf "${BACKUP_FILE}" \
    -C "${PROJECT_DIR}" \
    data/ \
    config.yaml \
    2>/dev/null || true

# 30일 이상 삭제
find "${BACKUP_DIR}" -name "backup_*.tar.gz" -mtime +30 -delete

echo "Backup: ${BACKUP_FILE}"
