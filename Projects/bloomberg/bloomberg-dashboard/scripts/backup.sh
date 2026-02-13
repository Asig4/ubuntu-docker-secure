#!/bin/bash
# ============================================================
# Bloomberg Dashboard — Script de backup automatique
# ============================================================
# Usage: ./scripts/backup.sh
# Cron: 0 3 * * * /home/bloomberg/bloomberg-dashboard/scripts/backup.sh

set -euo pipefail

# Charger les variables d'environnement
source "$(dirname "$0")/../.env"

BACKUP_DIR="/home/bloomberg/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "$(date '+%Y-%m-%d %H:%M:%S') === Début du backup ==="

# --- PostgreSQL ---
echo "Backup PostgreSQL..."
docker exec bloomberg-postgres pg_dump \
  -U "$POSTGRES_USER" bloomberg_config > "$BACKUP_DIR/postgres.sql"
echo "  → postgres.sql ($(du -sh "$BACKUP_DIR/postgres.sql" | cut -f1))"

# --- InfluxDB ---
echo "Backup InfluxDB..."
docker exec bloomberg-influxdb influx backup \
  /tmp/influx-backup \
  --org bloomberg \
  -t "$INFLUXDB_TOKEN" 2>/dev/null
docker cp bloomberg-influxdb:/tmp/influx-backup "$BACKUP_DIR/influxdb/"
docker exec bloomberg-influxdb rm -rf /tmp/influx-backup
echo "  → influxdb/ ($(du -sh "$BACKUP_DIR/influxdb/" | cut -f1))"

# --- Grafana Dashboards ---
echo "Backup Grafana dashboards..."
cp -r "$(dirname "$0")/../grafana/dashboards-json/" "$BACKUP_DIR/dashboards/"
echo "  → dashboards/"

# --- Configuration ---
echo "Backup configuration..."
cp "$(dirname "$0")/../.env" "$BACKUP_DIR/dot-env-backup"
cp "$(dirname "$0")/../docker-compose.yml" "$BACKUP_DIR/"
echo "  → config files"

# --- Compression ---
echo "Compression..."
ARCHIVE="$BACKUP_DIR.tar.gz"
tar -czf "$ARCHIVE" -C "$(dirname "$BACKUP_DIR")" "$(basename "$BACKUP_DIR")"
rm -rf "$BACKUP_DIR"

SIZE=$(du -sh "$ARCHIVE" | cut -f1)
echo "$(date '+%Y-%m-%d %H:%M:%S') === Backup terminé: $ARCHIVE ($SIZE) ==="

# --- Nettoyage des vieux backups (> 30 jours) ---
DELETED=$(find /home/bloomberg/backups -name "*.tar.gz" -mtime +30 -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
  echo "Nettoyé $DELETED ancien(s) backup(s)"
fi
