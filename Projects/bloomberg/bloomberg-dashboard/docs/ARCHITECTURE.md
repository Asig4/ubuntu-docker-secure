# Architecture Technique

> Vue d'ensemble de l'architecture du Bloomberg Dashboard.

## Schéma Global

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         VPS DÉDIÉ (Ubuntu 22.04)                        │
│                    4 vCPU │ 8 GB RAM │ 80 GB SSD                        │
│                                                                         │
│  ┌─────────────────────── COUCHE PRÉSENTATION ────────────────────────┐  │
│  │                                                                     │  │
│  │   ┌──────────────┐         ┌──────────────────────────┐            │  │
│  │   │   NGINX      │ ◄─────► │       GRAFANA 11+        │            │  │
│  │   │   :80/:443   │  proxy  │        :3000              │            │  │
│  │   │   SSL/TLS    │         │  • Dashboards Bloomberg   │            │  │
│  │   │   Rate limit │         │  • Variables dynamiques   │            │  │
│  │   └──────────────┘         │  • Alerting engine        │            │  │
│  │                             │  • Plugins custom         │            │  │
│  │                             └─────────┬────────────────┘            │  │
│  └───────────────────────────────────────┼────────────────────────────┘  │
│                                           │                              │
│  ┌─────────────────────── COUCHE DONNÉES ─┼───────────────────────────┐  │
│  │                                        │                            │  │
│  │   ┌────────────┐  ┌───────────────┐  ┌┴───────────┐               │  │
│  │   │ InfluxDB   │  │  PostgreSQL   │  │ Prometheus  │               │  │
│  │   │   2.x      │  │     16        │  │             │               │  │
│  │   │  :8086     │  │   :5432       │  │   :9090     │               │  │
│  │   │            │  │               │  │             │               │  │
│  │   │ Buckets:   │  │ Tables:       │  │ Targets:    │               │  │
│  │   │ • markets  │  │ • watchlists  │  │ • node_exp  │               │  │
│  │   │ • news     │  │ • layouts     │  │ • cadvisor  │               │  │
│  │   │ • infra    │  │ • alert_rules │  │ • grafana   │               │  │
│  │   │ • custom   │  │ • users       │  │ • influxdb  │               │  │
│  │   └─────▲──────┘  └──────▲────────┘  └──────▲──────┘               │  │
│  └─────────┼────────────────┼──────────────────┼──────────────────────┘  │
│            │                │                   │                         │
│  ┌─────────┼── COUCHE COLLECTE ─────────────────┼─────────────────────┐  │
│  │         │                │                   │                      │  │
│  │  ┌──────┴─────┐  ┌──────┴──────┐  ┌────────┴────────┐            │  │
│  │  │  Market    │  │  Watchlist  │  │  Node Exporter  │            │  │
│  │  │  Feeder    │  │  Manager    │  │    :9100        │            │  │
│  │  │  (Python)  │  │  (FastAPI)  │  ├─────────────────┤            │  │
│  │  │            │  │   :8000     │  │  cAdvisor       │            │  │
│  │  │  + News    │  │             │  │    :8081        │            │  │
│  │  │  Feeder    │  │  CRUD API   │  │                 │            │  │
│  │  └──────▲─────┘  └─────────────┘  └─────────────────┘            │  │
│  └─────────┼─────────────────────────────────────────────────────────┘  │
│            │                                                             │
│  ┌─────────┼────── COUCHE EXTERNE ───────────────────────────────────┐  │
│  │         │                                                          │  │
│  │   ┌─────┴──────────────────────────────────────────────────────┐  │  │
│  │   │                      APIs Externes                         │  │  │
│  │   │                                                            │  │  │
│  │   │  Binance WS    CoinGecko     Yahoo Finance   Alpha Vantage │  │  │
│  │   │  (real-time)   (market cap)  (stocks/forex)  (fallback)    │  │  │
│  │   │                                                            │  │  │
│  │   │  CryptoPanic   NewsAPI       RSS Feeds       ExchangeRate  │  │  │
│  │   │  (crypto news) (general)     (custom)        (forex)       │  │  │
│  │   └────────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────── COUCHE ALERTING ────────────────────────────┐  │
│  │                                                                     │  │
│  │   Grafana Alerting → Alertmanager → Telegram Bot                   │  │
│  │                                   → Email (SMTP)                    │  │
│  │                                   → Webhook (Discord/Slack/Custom)  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Flux de Données

### 1. Flux Market Data

```
Binance WebSocket ──► Market Feeder ──► InfluxDB (bucket: markets)
                        │                    │
Yahoo Finance REST ─────┤                    ├──► Grafana (panels prix)
                        │                    │
CoinGecko REST ─────────┘                    └──► Grafana (alerting)
```

**Fréquence** :
- WebSocket Binance : temps réel (1-5 secondes)
- REST Yahoo Finance : toutes les 15 secondes
- REST CoinGecko : toutes les 60 secondes (rate limit gratuit)

**Format de données InfluxDB** :
```flux
// Measurement: market_data
// Tags: exchange, symbol, asset_type
// Fields: price, volume_24h, change_pct_1h, change_pct_24h, market_cap
// Timestamp: nanoseconds

market_data,exchange=binance,symbol=BTC/USDT,asset_type=crypto price=67234.50,volume_24h=28500000000,change_pct_1h=0.45,change_pct_24h=2.3,market_cap=1320000000000 1707753600000000000
```

### 2. Flux News

```
CryptoPanic API ────► News Feeder ──► Sentiment Analysis ──► InfluxDB (bucket: news)
                        │                                          │
NewsAPI ────────────────┤                                          └──► Grafana (news panel)
                        │
RSS Feeds ──────────────┘
```

**Fréquence** : polling toutes les 2-5 minutes
**Format** :
```flux
// Measurement: news_articles
// Tags: source, category, related_asset
// Fields: title, url, sentiment_score, published_at

news_articles,source=cryptopanic,category=crypto,related_asset=BTC title="Bitcoin hits new high",url="https://...",sentiment_score=0.75 1707753600000000000
```

### 3. Flux Infrastructure

```
Node Exporter ──► Prometheus ──► Grafana (infra panels)
cAdvisor ───────►              │
                                └──► Alertmanager ──► Telegram/Email
```

**Métriques collectées** :
- CPU : utilisation %, load average, température
- RAM : utilisée, disponible, swap
- Disque : espace, I/O, latence
- Réseau : bandwidth in/out, packets, erreurs
- Docker : CPU/RAM par container, restart count, uptime

### 4. Flux Watchlists

```
Utilisateur ──► FastAPI (CRUD) ──► PostgreSQL
                    │
                    └──► Notification au Market Feeder
                              │
                              └──► Ajuste les assets collectés dynamiquement
```

## Réseau Docker

```
bloomberg-net (bridge)
│
├── bloomberg-grafana      (3000)
├── bloomberg-influxdb     (8086)
├── bloomberg-postgres     (5432)
├── bloomberg-prometheus   (9090)
├── bloomberg-market-feeder
├── bloomberg-news-feeder
├── bloomberg-watchlist-api (8000)
├── bloomberg-node-exporter (9100)
├── bloomberg-cadvisor     (8081)
└── bloomberg-nginx        (80, 443) ← seul exposé à l'extérieur
```

**Règle critique** : seul Nginx expose des ports vers l'extérieur. Tous les autres services communiquent uniquement sur le réseau Docker interne.

## Rétention des Données

| Bucket/Table | Rétention | Downsampling | Volume estimé/mois |
|-------------|-----------|--------------|---------------------|
| `markets` (raw) | 7 jours | — | ~5 GB |
| `markets` (5min) | 30 jours | InfluxDB Task | ~500 MB |
| `markets` (1h) | 365 jours | InfluxDB Task | ~50 MB |
| `news` | 90 jours | — | ~200 MB |
| `infra` | 15 jours | — | ~1 GB |
| `custom` | illimité | — | variable |
| PostgreSQL | illimité | — | ~100 MB |

### InfluxDB Tasks (Downsampling automatique)

```flux
// Task: downsample_5min (exécuté toutes les 5 minutes)
option task = {name: "downsample_5min", every: 5m}

from(bucket: "markets")
  |> range(start: -10m)
  |> filter(fn: (r) => r._measurement == "market_data")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
  |> to(bucket: "markets_5min", org: "bloomberg")
```

## Dimensionnement

### Ressources par container

| Container | CPU max | RAM max | Disque |
|-----------|---------|---------|--------|
| Grafana | 1 CPU | 1 GB | 500 MB |
| InfluxDB | 2 CPU | 3 GB | 30 GB |
| PostgreSQL | 0.5 CPU | 512 MB | 2 GB |
| Prometheus | 1 CPU | 1 GB | 10 GB |
| Market Feeder | 0.5 CPU | 512 MB | 100 MB |
| News Feeder | 0.25 CPU | 256 MB | 50 MB |
| Watchlist API | 0.25 CPU | 256 MB | 50 MB |
| Node Exporter | 0.1 CPU | 64 MB | — |
| cAdvisor | 0.25 CPU | 256 MB | — |
| Nginx | 0.25 CPU | 128 MB | 50 MB |

**Total estimé** : ~3.5 CPU, ~6 GB RAM, ~43 GB disque

### Recommandation VPS

| Charge | vCPU | RAM | SSD | Coût estimé |
|--------|------|-----|-----|-------------|
| 1-2 users, 20 assets | 4 | 8 GB | 80 GB | ~15€/mois |
| 3-5 users, 50 assets | 4 | 16 GB | 160 GB | ~25€/mois |
| 5+ users, 100+ assets | 8 | 32 GB | 320 GB | ~50€/mois |

## Sécurité réseau

```
Internet
    │
    ▼
┌─────────┐
│  UFW    │  Ports ouverts : 22 (SSH), 80, 443
│Firewall │  Tout le reste : DENY
└────┬────┘
     │
     ▼
┌─────────┐
│  Nginx  │  Rate limiting : 10 req/s par IP
│  + SSL  │  Headers : HSTS, CSP, X-Frame-Options
│         │  SSL : Let's Encrypt via Certbot
└────┬────┘
     │
     ▼
┌─────────┐
│ Docker  │  Réseau isolé : bloomberg-net
│ Network │  Pas de port exposé sauf Nginx
└─────────┘
```

## Points de défaillance et mitigation

| Composant | Impact si down | Mitigation |
|-----------|---------------|------------|
| InfluxDB | Plus de données temps réel | Backup quotidien, alerting |
| PostgreSQL | Plus de config/watchlists | Backup quotidien, réplication possible |
| Market Feeder | Données stoppées | Health check + auto-restart Docker |
| News Feeder | News stoppées | Health check + auto-restart |
| Prometheus | Plus de monitoring infra | Alertmanager dead man's switch |
| Nginx | Dashboard inaccessible | Accès direct Grafana :3000 en backup |
| Grafana | Dashboard inaccessible | Provisioning = rebuild instantané |
