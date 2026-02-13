#!/bin/bash
# ============================================================
# Bloomberg Dashboard — Health Check rapide
# ============================================================
# Usage: ./scripts/healthcheck.sh

set -uo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================="
echo "  Bloomberg Dashboard — Health Check"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="
echo ""

check_service() {
    local name=$1
    local container=$2
    local status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no-healthcheck")
    local running=$(docker inspect --format='{{.State.Running}}' "$container" 2>/dev/null || echo "false")

    if [ "$running" = "true" ]; then
        if [ "$status" = "healthy" ]; then
            printf "  ${GREEN}✓${NC} %-25s %s\n" "$name" "healthy"
        elif [ "$status" = "no-healthcheck" ]; then
            printf "  ${YELLOW}~${NC} %-25s %s\n" "$name" "running (no healthcheck)"
        else
            printf "  ${YELLOW}!${NC} %-25s %s\n" "$name" "$status"
        fi
    else
        printf "  ${RED}✗${NC} %-25s %s\n" "$name" "DOWN"
    fi
}

echo "--- Services ---"
check_service "Grafana" "bloomberg-grafana"
check_service "InfluxDB" "bloomberg-influxdb"
check_service "PostgreSQL" "bloomberg-postgres"
check_service "Prometheus" "bloomberg-prometheus"
check_service "Market Feeder" "bloomberg-market-feeder"
check_service "News Feeder" "bloomberg-news-feeder"
check_service "Watchlist API" "bloomberg-watchlist-api"
check_service "Node Exporter" "bloomberg-node-exporter"
check_service "cAdvisor" "bloomberg-cadvisor"
check_service "Nginx" "bloomberg-nginx"

echo ""
echo "--- Ressources VPS ---"
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' 2>/dev/null || echo "N/A")
MEM_TOTAL=$(free -h | awk '/^Mem:/{print $2}')
MEM_USED=$(free -h | awk '/^Mem:/{print $3}')
DISK_USAGE=$(df -h / | awk 'NR==2{print $5}')

printf "  CPU:    %s%%\n" "$CPU_USAGE"
printf "  RAM:    %s / %s\n" "$MEM_USED" "$MEM_TOTAL"
printf "  Disque: %s utilisé\n" "$DISK_USAGE"

echo ""
echo "--- Données récentes ---"
source "$(dirname "$0")/../.env" 2>/dev/null

MARKET_COUNT=$(docker exec bloomberg-influxdb influx query \
  'from(bucket:"markets") |> range(start:-5m) |> count() |> sum()' \
  --org bloomberg -t "$INFLUXDB_TOKEN" 2>/dev/null | tail -1 | awk '{print $NF}' || echo "N/A")
printf "  Points marchés (5 min): %s\n" "$MARKET_COUNT"

echo ""
echo "========================================="
