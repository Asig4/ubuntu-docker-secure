#!/usr/bin/env bash
# ============================================================
# Bloomberg Dashboard — Phase 1 Setup Script
# ============================================================
# Idempotent: safe to run multiple times
# Creates InfluxDB buckets, inserts test data, verifies all datasources
#
# Usage: ./scripts/setup-phase1.sh
# ============================================================

set -euo pipefail

# Load .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; }
info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

ERRORS=0

# ============================================================
# Step 1: Create InfluxDB buckets
# ============================================================
info "Creating InfluxDB buckets..."

create_bucket() {
    local name=$1
    local retention=$2
    # Check if bucket exists
    if docker exec bloomberg-influxdb influx bucket list \
        --org bloomberg --token "$INFLUXDB_TOKEN" 2>/dev/null | grep -q "$name"; then
        ok "Bucket '$name' already exists"
    else
        if docker exec bloomberg-influxdb influx bucket create \
            --name "$name" --org bloomberg --token "$INFLUXDB_TOKEN" \
            --retention "$retention" 2>/dev/null; then
            ok "Bucket '$name' created (retention: $retention)"
        else
            fail "Could not create bucket '$name'"
            ((ERRORS++))
        fi
    fi
}

create_bucket "news"         "2160h"
create_bucket "infra"        "360h"
create_bucket "custom"       "0"
create_bucket "markets_5min" "720h"
create_bucket "markets_1h"   "8760h"

# ============================================================
# Step 2: Write test data to InfluxDB
# ============================================================
info "Writing test data to InfluxDB..."

write_influx() {
    local bucket=$1
    local data=$2
    if docker exec bloomberg-influxdb influx write \
        --bucket "$bucket" --org bloomberg --token "$INFLUXDB_TOKEN" \
        --precision s "$data" 2>/dev/null; then
        ok "Test data written to '$bucket'"
    else
        fail "Could not write to '$bucket'"
        ((ERRORS++))
    fi
}

NOW=$(date +%s)

write_influx "markets" "price,symbol=BTCUSDT,exchange=binance last=97500.50,bid=97499.00,ask=97502.00,volume=1234.56 $NOW"
write_influx "markets" "price,symbol=ETHUSDT,exchange=binance last=3250.75,bid=3250.00,ask=3251.50,volume=8765.43 $NOW"
write_influx "news"    "article,source=cryptopanic,sentiment=positive title=\"BTC breaks 97k\",score=0.85 $NOW"
write_influx "infra"   "container_stats,container=bloomberg-grafana cpu_pct=2.5,mem_mb=256.0 $NOW"

# ============================================================
# Step 3: Verify InfluxDB read
# ============================================================
info "Verifying InfluxDB read (Flux query)..."

FLUX_RESULT=$(docker exec bloomberg-influxdb influx query \
    --org bloomberg --token "$INFLUXDB_TOKEN" \
    'from(bucket: "markets") |> range(start: -1h) |> filter(fn: (r) => r._measurement == "price") |> limit(n: 1)' 2>&1)

if echo "$FLUX_RESULT" | grep -q "BTCUSDT\|ETHUSDT"; then
    ok "InfluxDB Flux query returned test data"
else
    fail "InfluxDB Flux query did not return expected data"
    ((ERRORS++))
fi

# ============================================================
# Step 4: Verify PostgreSQL tables and data
# ============================================================
info "Verifying PostgreSQL tables..."

PG_TABLES=$(docker exec bloomberg-postgres psql -U "$POSTGRES_USER" -d bloomberg_config \
    -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;" 2>&1)

for table in alert_rules api_users user_layouts watchlists; do
    if echo "$PG_TABLES" | grep -q "$table"; then
        ok "Table '$table' exists"
    else
        fail "Table '$table' missing"
        ((ERRORS++))
    fi
done

# Check default watchlists
WL_COUNT=$(docker exec bloomberg-postgres psql -U "$POSTGRES_USER" -d bloomberg_config \
    -t -c "SELECT COUNT(*) FROM watchlists;" 2>&1 | tr -d ' ')

if [[ "$WL_COUNT" -ge 2 ]]; then
    ok "Default watchlists present ($WL_COUNT rows)"
else
    fail "Expected at least 2 watchlists, got $WL_COUNT"
    ((ERRORS++))
fi

# Insert test data: user_layouts
info "Inserting test data into PostgreSQL..."

docker exec bloomberg-postgres psql -U "$POSTGRES_USER" -d bloomberg_config -c "
INSERT INTO user_layouts (user_id, layout_name, panels_config, is_default) VALUES
(1, 'Default Bloomberg', '{\"panels\": [\"ticker\", \"chart\", \"news\", \"watchlist\"]}', true)
ON CONFLICT (user_id, layout_name) DO NOTHING;
" 2>/dev/null && ok "Test layout inserted" || { fail "Could not insert test layout"; ((ERRORS++)); }

docker exec bloomberg-postgres psql -U "$POSTGRES_USER" -d bloomberg_config -c "
INSERT INTO alert_rules (user_id, name, asset, condition, threshold, channel) VALUES
(1, 'BTC above 100k', 'BTC/USDT', 'above', 100000, 'telegram')
ON CONFLICT DO NOTHING;
" 2>/dev/null && ok "Test alert rule inserted" || { fail "Could not insert test alert rule"; ((ERRORS++)); }

# ============================================================
# Step 5: Verify Prometheus targets
# ============================================================
info "Checking Prometheus targets..."

PROM_TARGETS=$(curl -s http://localhost:9090/api/v1/targets 2>&1)

check_target() {
    local job=$1
    local expected=$2
    local state
    state=$(echo "$PROM_TARGETS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for t in data.get('data', {}).get('activeTargets', []):
    if t.get('labels', {}).get('job') == '$job':
        print(t.get('health', 'unknown'))
        break
else:
    print('not_found')
" 2>/dev/null || echo "parse_error")

    if [[ "$state" == "$expected" ]]; then
        ok "Prometheus target '$job' is $state"
    elif [[ "$expected" == "any" ]]; then
        ok "Prometheus target '$job' state: $state"
    else
        fail "Prometheus target '$job' is $state (expected $expected)"
        ((ERRORS++))
    fi
}

check_target "prometheus"     "up"
check_target "node-exporter"  "up"
check_target "cadvisor"       "up"
check_target "grafana"        "up"
check_target "market-feeder"  "any"
check_target "watchlist-api"  "any"

# ============================================================
# Step 6: Verify Grafana datasources
# ============================================================
info "Checking Grafana datasource health..."

GRAFANA_AUTH="admin:${GRAFANA_ADMIN_PASSWORD}"

check_datasource() {
    local name=$1
    local uid
    uid=$(curl -s -u "$GRAFANA_AUTH" "http://localhost/api/datasources/name/$name" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('uid', ''))
" 2>/dev/null || echo "")

    if [[ -z "$uid" ]]; then
        fail "Datasource '$name' not found in Grafana"
        ((ERRORS++))
        return
    fi

    local health
    health=$(curl -s -u "$GRAFANA_AUTH" "http://localhost/api/datasources/uid/$uid/health" 2>/dev/null)
    local status
    status=$(echo "$health" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('status', 'unknown'))
" 2>/dev/null || echo "error")

    if [[ "$status" == "OK" || "$status" == "ok" ]]; then
        ok "Grafana datasource '$name' health: OK"
    else
        fail "Grafana datasource '$name' health: $status"
        echo "  Response: $health"
        ((ERRORS++))
    fi
}

check_datasource "InfluxDB"
check_datasource "PostgreSQL"
check_datasource "Prometheus"

# ============================================================
# Summary
# ============================================================
echo ""
echo "============================================================"
if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}Phase 1 setup completed successfully — 0 errors${NC}"
else
    echo -e "${RED}Phase 1 setup completed with $ERRORS error(s)${NC}"
fi
echo "============================================================"

exit $ERRORS
