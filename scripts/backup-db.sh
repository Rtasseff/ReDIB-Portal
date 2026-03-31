#!/bin/bash
# ============================================================================
# ReDIB Portal - Backup Script (Database + Key Files)
# ============================================================================
# Usage:
#   ./scripts/backup-db.sh
#
# Cron example (daily at 2 AM, keep 30 days):
#   0 2 * * * cd /home/deploy/ReDIB-Portal && ./scripts/backup-db.sh >> /home/deploy/backups/redib/backup.log 2>&1
#
# IMPORTANT: The "cd /home/deploy/ReDIB-Portal &&" prefix is required because
# this script uses a relative path to docker-compose.prod.yml. Without it,
# cron runs from the home directory and the script will silently fail.
# ============================================================================

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/home/deploy/backups/redib}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/redib_db_${TIMESTAMP}.sql.gz"
FILES_BACKUP="${BACKUP_DIR}/redib_files_${TIMESTAMP}.tar.gz"

# Files/directories to back up (paths relative to project root).
# Edit this list to add anything not tracked in git.
BACKUP_FILES=(
    ".env"
)

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting database backup..."

# Dump database from the running PostgreSQL container
docker compose -f "${COMPOSE_FILE}" exec -T db \
    pg_dump -U "${POSTGRES_USER:-redib_user}" -d "${POSTGRES_DB:-redib_db}" \
    --no-owner --no-acl \
    | gzip > "${BACKUP_FILE}"

# Verify backup is not empty
if [ ! -s "${BACKUP_FILE}" ]; then
    echo "[$(date)] ERROR: Backup file is empty!"
    rm -f "${BACKUP_FILE}"
    exit 1
fi

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "[$(date)] Backup completed: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Back up key files not tracked in git
VALID_FILES=()
for f in "${BACKUP_FILES[@]}"; do
    if [ -e "${f}" ]; then
        VALID_FILES+=("${f}")
    else
        echo "[$(date)] WARNING: ${f} not found, skipping"
    fi
done

if [ ${#VALID_FILES[@]} -gt 0 ]; then
    tar -czf "${FILES_BACKUP}" "${VALID_FILES[@]}"
    FILES_SIZE=$(du -h "${FILES_BACKUP}" | cut -f1)
    echo "[$(date)] Files backup completed: ${FILES_BACKUP} (${FILES_SIZE})"
else
    echo "[$(date)] No files to back up, skipping file archive"
fi

# Remove backups older than retention period
DB_DELETED=$(find "${BACKUP_DIR}" -name "redib_db_*.sql.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
FILES_DELETED=$(find "${BACKUP_DIR}" -name "redib_files_*.tar.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
TOTAL_DELETED=$((DB_DELETED + FILES_DELETED))
if [ "${TOTAL_DELETED}" -gt 0 ]; then
    echo "[$(date)] Cleaned up ${TOTAL_DELETED} old backup(s)"
fi

echo "[$(date)] Backup finished successfully."
