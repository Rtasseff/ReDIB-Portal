#!/bin/bash
# ============================================================================
# ReDIB Portal - Backup Script (Database + Key Files)
# ============================================================================
# Usage:
#   ./scripts/backup-db.sh
#
# Cron example (daily at 2 AM, keep 7 days):
#   0 2 * * * cd /home/deploy/ReDIB-Portal && ./scripts/backup-db.sh >> /home/deploy/backups/redib/backup.log 2>&1
#
# IMPORTANT: The "cd /home/deploy/ReDIB-Portal &&" prefix is required because
# this script uses a relative path to docker-compose.prod.yml. Without it,
# cron runs from the home directory and the script will silently fail.
#
# ----------------------------------------------------------------------------
# Pruning-safety model
# ----------------------------------------------------------------------------
# The retention prune (`find -mtime +N -delete`) runs ONLY after the current
# run has produced a verifiably good backup. Any failure — hard error, empty
# file, missing pg_dump header, or a suspiciously small dump — aborts the
# script with `exit 1` BEFORE the prune step. Consequences:
#
#   * If today's backup is broken, yesterday's (and older) backups are kept.
#   * Repeated silent failures cause junk files to pile up, not data loss.
#     We would rather accumulate bad/useless backups than auto-delete the
#     last known-good one while corruption goes unnoticed.
#   * Restoration is a human decision: check backup.log, inspect the
#     preserved bad dumps, then choose which .sql.gz to restore from.
#
# Validation gates (in order — each one must pass to reach the prune step):
#   1. set -euo pipefail — any command failure in the dump pipeline aborts.
#   2. Non-empty check   — dump file must be >0 bytes.
#   3. Header check      — first ~20 decompressed lines must contain the
#                          PostgreSQL dump marker. Catches gzip-of-empty,
#                          wrong DB, role with no SELECT perms, etc.
#   4. Size ratio check  — dump must be at least MIN_SIZE_RATIO_PERCENT of
#                          the most recent prior dump. Catches truncated or
#                          partial dumps where the header is fine but the
#                          body is missing. Skipped on the very first run.
#
# Overrides (env vars): RETENTION_DAYS, MIN_SIZE_RATIO_PERCENT, BACKUP_DIR.
# Example after a legitimate DB shrinkage:
#   MIN_SIZE_RATIO_PERCENT=10 ./scripts/backup-db.sh
#
# ----------------------------------------------------------------------------
# Alerting
# ----------------------------------------------------------------------------
# Two independent channels — each catches failure modes the other misses.
#
# 1. In-script email (via the Django send_ops_alert management command):
#      - Fires on any non-zero exit (validation failure, docker error, etc.).
#      - Sent synchronously through the portal's existing SMTP setup, so the
#        From: address is noreply@redib.net and no extra creds live on the
#        host. Recipient defaults to coordinator@redib.net (ALERT_RECIPIENT).
#      - Does NOT catch: cron down, host off, script deleted, web container
#        down — in those cases the email itself can't be sent.
#
# 2. Deadman-switch ping (optional, external service such as healthchecks.io):
#      - On successful completion the script hits HEALTHCHECK_URL once.
#      - If the ping never arrives (the failure modes the email can't catch),
#        the service pages you after its grace period.
#      - Leave HEALTHCHECK_URL empty to disable. Set it in .env once you have
#        a URL from the service; no other changes needed.
#
# Env vars:
#   ALERT_RECIPIENT    — email address for failure alerts (default
#                        coordinator@redib.net).
#   HEALTHCHECK_URL    — URL to GET on success (default empty = no ping).
# ============================================================================

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/home/deploy/backups/redib}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
MIN_SIZE_RATIO_PERCENT="${MIN_SIZE_RATIO_PERCENT:-50}"
ALERT_RECIPIENT="${ALERT_RECIPIENT:-coordinator@redib.net}"
HEALTHCHECK_URL="${HEALTHCHECK_URL:-}"
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

# ----------------------------------------------------------------------------
# Alerting helpers
# ----------------------------------------------------------------------------
# send_alert: shells into the `web` container and runs the send_ops_alert
# Django command synchronously. The `|| echo` guard prevents a failed alert
# send from masking the original script failure — the original exit code is
# preserved by the EXIT trap (see below).
send_alert() {
    local subject="$1"
    local body="$2"
    docker compose -f "${COMPOSE_FILE}" exec -T web \
        python manage.py send_ops_alert \
        --recipient "${ALERT_RECIPIENT}" \
        --subject "${subject}" \
        --body "${body}" 2>&1 \
        || echo "[$(date)] WARNING: alert email failed to send" >&2
}

# EXIT trap: fires once when the script exits for any reason. If the exit
# code is non-zero (any validation gate failed, docker error, etc.), send
# an alert email. We guard against re-entry with ALERT_FIRED so nested
# failures in send_alert itself don't loop.
ALERT_FIRED=0
on_exit() {
    local rc=$?
    if [ "${rc}" -ne 0 ] && [ "${ALERT_FIRED}" -eq 0 ]; then
        ALERT_FIRED=1
        send_alert \
            "[ReDIB backup] FAILED on $(hostname)" \
            "Backup script exited ${rc} at $(date).

Host:       $(hostname)
Backup dir: ${BACKUP_DIR}

Latest log entries:
$(tail -n 20 "${BACKUP_DIR}/backup.log" 2>/dev/null || echo '(no log available)')

Any suspicious dump files are preserved in ${BACKUP_DIR} for inspection.
Do NOT delete them until the failure is diagnosed."
    fi
}
trap on_exit EXIT

echo "[$(date)] Starting database backup..."

# Dump database from the running PostgreSQL container
docker compose -f "${COMPOSE_FILE}" exec -T db \
    pg_dump -U "${POSTGRES_USER:-redib_user}" -d "${POSTGRES_DB:-redib_db}" \
    --no-owner --no-acl \
    | gzip > "${BACKUP_FILE}"

# --- Validation gate 2: non-empty ---
# A 0-byte file means the redirect or gzip never produced output. Remove
# it (nothing to inspect) and abort BEFORE the prune step so older backups
# survive.
if [ ! -s "${BACKUP_FILE}" ]; then
    echo "[$(date)] ERROR: Backup file is empty — aborting before prune." >&2
    rm -f "${BACKUP_FILE}"
    exit 1
fi

# --- Validation gate 3: PostgreSQL dump header ---
# gzip of an empty stream is ~20 bytes and would pass the non-empty check,
# and pg_dump can legitimately exit 0 with useless output (wrong DB name,
# role without SELECT perms, etc.). A real dump always starts with a
# "PostgreSQL database dump" marker comment. If it's missing, something
# went wrong silently — preserve the bad file for inspection and abort
# BEFORE the prune step.
#
# Note on `|| true`: `head` closes gunzip's pipe after 20 lines, which
# raises SIGPIPE on gunzip. Under `set -o pipefail` that would look like a
# pipeline failure. We only care about whether grep found the marker, so
# we swallow the pipeline exit code and check the match count directly.
HEADER_MATCH=$(gunzip -c "${BACKUP_FILE}" 2>/dev/null | head -n 20 | grep -c 'PostgreSQL database dump' || true)
if [ "${HEADER_MATCH:-0}" -eq 0 ]; then
    echo "[$(date)] ERROR: Backup missing PostgreSQL dump header — aborting before prune." >&2
    echo "[$(date)]        Suspicious dump preserved at ${BACKUP_FILE} for inspection." >&2
    exit 1
fi

# --- Validation gate 4: size sanity vs last known-good backup ---
# Catches partial/truncated dumps where the header renders correctly but
# the body is silently missing data. We compare today's compressed size
# against the newest prior *.sql.gz (excluding the one we just wrote). On
# the very first run there is no prior, so the check is skipped. If the
# DB legitimately shrinks, override with MIN_SIZE_RATIO_PERCENT=<lower>.
CURRENT_SIZE=$(stat -c%s "${BACKUP_FILE}")
PRIOR_FILE=$(find "${BACKUP_DIR}" -maxdepth 1 -name "redib_db_*.sql.gz" ! -path "${BACKUP_FILE}" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -n 1 | cut -d' ' -f2- || true)

if [ -n "${PRIOR_FILE:-}" ]; then
    PRIOR_SIZE=$(stat -c%s "${PRIOR_FILE}")
    MIN_SIZE=$(( PRIOR_SIZE * MIN_SIZE_RATIO_PERCENT / 100 ))
    if [ "${CURRENT_SIZE}" -lt "${MIN_SIZE}" ]; then
        echo "[$(date)] ERROR: Backup size ${CURRENT_SIZE}B is below ${MIN_SIZE_RATIO_PERCENT}% of prior ${PRIOR_SIZE}B (${PRIOR_FILE##*/}) — aborting before prune." >&2
        echo "[$(date)]        Suspicious dump preserved at ${BACKUP_FILE} for inspection." >&2
        echo "[$(date)]        If the shrinkage is legitimate, rerun with MIN_SIZE_RATIO_PERCENT=<lower value>." >&2
        exit 1
    fi
    echo "[$(date)] Size check passed: ${CURRENT_SIZE}B vs prior ${PRIOR_SIZE}B (threshold ${MIN_SIZE_RATIO_PERCENT}%)."
else
    echo "[$(date)] No prior backup for size comparison — skipping ratio check (first run)."
fi

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "[$(date)] Backup validated: ${BACKUP_FILE} (${BACKUP_SIZE})"

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

# --- Retention pruning ---
# Only reached when every validation gate above has passed. If any gate
# failed we already exited 1, so older backups stay on disk. This is
# intentional: we would rather accumulate failed-run artifacts than
# auto-delete the last known-good backup while silent corruption goes
# unnoticed. See the "Pruning-safety model" header block for details.
DB_DELETED=$(find "${BACKUP_DIR}" -name "redib_db_*.sql.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
FILES_DELETED=$(find "${BACKUP_DIR}" -name "redib_files_*.tar.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
TOTAL_DELETED=$((DB_DELETED + FILES_DELETED))
if [ "${TOTAL_DELETED}" -gt 0 ]; then
    echo "[$(date)] Cleaned up ${TOTAL_DELETED} old backup(s) older than ${RETENTION_DAYS} days"
fi

# --- Deadman-switch ping ---
# Reached only on full success (any earlier exit 1 short-circuits this).
# Hitting HEALTHCHECK_URL tells the external monitor "we ran, we're fine".
# If the ping never arrives — because cron died, the host is off, etc. —
# the external service pages the operator. See DEPLOYMENT.md §6.3 for
# how to get a URL from healthchecks.io (or equivalent). Empty = disabled.
if [ -n "${HEALTHCHECK_URL}" ]; then
    curl -fsS --max-time 10 --retry 3 "${HEALTHCHECK_URL}" > /dev/null \
        && echo "[$(date)] Deadman ping sent." \
        || echo "[$(date)] WARNING: deadman ping to ${HEALTHCHECK_URL} failed" >&2
fi

echo "[$(date)] Backup finished successfully."
