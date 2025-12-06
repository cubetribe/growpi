#!/bin/bash

# GrowPi Backup Script
# Backs up config.yaml and growpi.db to /home/admin/backups

BACKUP_DIR="/home/admin/backups"
DATE=$(date +%Y-%m-%d)
TARGET_DIR="$BACKUP_DIR/$DATE"
LOG_FILE="/var/log/grow-pi/backup.log"

# Ensure backup directory exists
mkdir -p "$TARGET_DIR"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log_message "Starting backup to $TARGET_DIR"

# Backup Config
if [ -f "/opt/grow-pi/config/config.yaml" ]; then
    cp "/opt/grow-pi/config/config.yaml" "$TARGET_DIR/"
    log_message "Backed up config.yaml"
else
    log_message "WARNING: config.yaml not found"
fi

# Backup Database (using sqlite3 .backup command for consistency if possible, else cp)
# Simple cp is risky for active DB, but acceptable for MVP if WAL mode is on.
# Better: use sqlite3 CLI to backup safely
if command -v sqlite3 &> /dev/null; then
    if [ -f "/opt/grow-pi/data/growpi.db" ]; then
        sqlite3 "/opt/grow-pi/data/growpi.db" ".backup '$TARGET_DIR/growpi.db'"
        log_message "Backed up growpi.db (sqlite3 safe backup)"
    else
        log_message "WARNING: growpi.db not found"
    fi
else
    # Fallback to copy
    if [ -f "/opt/grow-pi/data/growpi.db" ]; then
        cp "/opt/grow-pi/data/growpi.db" "$TARGET_DIR/"
        log_message "Backed up growpi.db (file copy - potential consistency risk)"
    fi
fi

# Retention Policy: Delete backups older than 30 days
find "$BACKUP_DIR" -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +
log_message "Cleaned up old backups"

log_message "Backup complete"
