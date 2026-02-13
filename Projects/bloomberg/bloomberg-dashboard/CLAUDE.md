# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

Planning/scaffolding phase. Documentation, configs and provisioning files exist. Still needed:
- `docker-compose.yml` (the core orchestration file)
- Python collectors in `collectors/` (all empty)
- Grafana dashboard JSON files in `grafana/dashboards-json/`

Follow `ROADMAP_Bloomberg_Dashboard.md` (parent directory) for phased implementation.

## Architecture

Bloomberg-style Grafana dashboard for crypto/forex/stocks, running entirely in Docker on a VPS.

**Data flow**: External APIs (Binance WS, CoinGecko, Yahoo Finance, NewsAPI, CryptoPanic) -> Python collectors -> InfluxDB (time-series) + PostgreSQL (config) -> Grafana dashboards -> Nginx reverse proxy -> User.

**Stack**: Grafana 11+ | InfluxDB 2.x (Flux only) | PostgreSQL 16 | Prometheus | FastAPI (Python 3.11+) | Nginx | Docker Compose v2

## Commands

```bash
# Start all services (once docker-compose.yml exists)
docker compose up -d

# Logs for a specific service
docker compose logs -f bloomberg-grafana

# Restart a collector
docker compose restart bloomberg-market-feeder

# Health check
docker compose ps
curl -s http://localhost:3000/api/health | jq

# Backup (PostgreSQL + InfluxDB + Grafana dashboards)
./scripts/backup.sh

# Generate secrets for .env
openssl rand -base64 24    # passwords
openssl rand -hex 32       # tokens
```

## Key Conventions

**InfluxDB**: Always use **Flux** query language, never InfluxQL. Org: `bloomberg`. Buckets: `markets`, `news`, `infra`, `custom`. Retention: 7d raw, 30d downsampled, 1y aggregated.

**PostgreSQL**: DB `bloomberg_config`. Schema in `scripts/init-db.sql` — 4 tables: `watchlists` (JSONB assets array), `user_layouts`, `alert_rules` (with CHECK constraints on condition/channel), `api_users`. All tables have `updated_at` auto-triggers.

**Docker networking**: All DB ports (8086, 5432, 9090) internal only on `bloomberg-net`. Only Nginx (80/443) exposed. Grafana (3000) and FastAPI (8000) accessed via Nginx proxy.

**Naming**: Python files `snake_case.py`, env vars `UPPER_SNAKE_CASE`, containers `bloomberg-{service}`, branches `feature/`, `fix/`, `docs/`, commits conventional (`feat:`, `fix:`, `docs:`, `chore:`).

**Language**: Code and comments in English, documentation in French.

## Bloomberg Visual Style

| Token | Value | Usage |
|-------|-------|-------|
| Background | `#0a0a0a` | Main background |
| Orange | `#ff8c00` | Titles, ticker text |
| Green | `#00d4aa` | Positive changes |
| Red | `#ff3b3b` | Negative changes |
| Borders | `#1a1a2e` | Panel separators |
| Font | `IBM Plex Mono` | All text (monospace) |

## Config Files

- `config/.env.example` — 68 env vars template (copy to `.env` at project root)
- `config/grafana.ini` — Grafana server config
- `config/nginx.conf` — Reverse proxy with SSL, rate limiting, security headers
- `config/prometheus.yml` — Scrape targets (node_exporter, cAdvisor, grafana, influxdb)
- `grafana/provisioning/datasources/datasources.yml` — Auto-provisions InfluxDB, PostgreSQL, Prometheus datasources
- `scripts/init-db.sql` — PostgreSQL schema (auto-executed via docker-entrypoint-initdb.d)

## Detailed Documentation

Read files in `docs/` before modifying related components:
- `ARCHITECTURE.md` — Full system diagram with 4 layers (presentation, data, collection, external)
- `COLLECTORS.md` — Python feeder specs (market, news, watchlist manager)
- `DASHBOARDS.md` — Panel specifications and Grafana variable setup
- `API.md` — FastAPI watchlist manager endpoints
- `DOCKER.md`, `SETUP.md`, `SECURITY.md`, `ALERTING.md`, `RUNBOOK.md`, `TROUBLESHOOTING.md`
