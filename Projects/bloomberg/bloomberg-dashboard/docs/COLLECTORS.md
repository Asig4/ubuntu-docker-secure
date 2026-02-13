# Collectors & Feeders

> Documentation des scripts Python qui alimentent les bases de données en temps réel.

## Vue d'ensemble

```
┌─────────────────────────────────────────────────┐
│                 COLLECTORS                        │
│                                                   │
│  ┌─────────────────┐  ┌─────────────────┐        │
│  │  Market Feeder  │  │  News Feeder    │        │
│  │                 │  │                 │        │
│  │  • Binance WS   │  │  • CryptoPanic  │        │
│  │  • Yahoo REST   │  │  • NewsAPI      │        │
│  │  • CoinGecko    │  │  • RSS Feeds    │        │
│  │  • Alpha Vant.  │  │  • Sentiment    │        │
│  │                 │  │                 │        │
│  │  → InfluxDB     │  │  → InfluxDB     │        │
│  │    (markets)    │  │    (news)       │        │
│  └─────────────────┘  └─────────────────┘        │
│                                                   │
│  ┌─────────────────┐                              │
│  │  Watchlist Mgr  │                              │
│  │  (FastAPI)      │                              │
│  │                 │                              │
│  │  → PostgreSQL   │                              │
│  │  → Notifie les  │                              │
│  │    feeders      │                              │
│  └─────────────────┘                              │
└─────────────────────────────────────────────────┘
```

## 1. Market Feeder

### Rôle
Collecte les prix, volumes et données de marché en temps réel depuis plusieurs sources, et les écrit dans InfluxDB.

### Structure des fichiers
```
collectors/market-feeder/
├── Dockerfile
├── requirements.txt
├── main.py                 # Point d'entrée
├── config.py               # Configuration depuis .env
├── health.py               # Endpoint /health
├── sources/
│   ├── __init__.py
│   ├── binance_ws.py       # WebSocket Binance (temps réel)
│   ├── yahoo_finance.py    # REST Yahoo Finance (stocks/forex)
│   ├── coingecko.py        # REST CoinGecko (market cap)
│   └── alpha_vantage.py    # REST Alpha Vantage (fallback)
├── processors/
│   ├── __init__.py
│   └── normalizer.py       # Normalisation des données
├── writers/
│   ├── __init__.py
│   └── influxdb_writer.py  # Écriture InfluxDB
└── tests/
    └── test_normalizer.py
```

### Dépendances (requirements.txt)
```
ccxt==4.2.0
influxdb-client[async]==1.40.0
websockets==12.0
aiohttp==3.9.0
python-dotenv==1.0.0
pydantic==2.6.0
fastapi==0.109.0
uvicorn==0.27.0
yfinance==0.2.36
pycoingecko==3.1.0
```

### Flux de données détaillé

```python
# Pseudo-code du flux principal
async def main():
    # 1. Lire la watchlist active depuis PostgreSQL
    assets = await get_active_watchlist()

    # 2. Démarrer les sources en parallèle
    tasks = [
        binance_websocket(assets.crypto),     # temps réel
        yahoo_finance_poll(assets.stocks),     # toutes les 15s
        coingecko_poll(assets.crypto),         # toutes les 60s
    ]
    await asyncio.gather(*tasks)
```

### Format de données (InfluxDB Line Protocol)

```
# Measurement: market_data
# Tags: exchange, symbol, asset_type (crypto/stock/forex/commodity/index)
# Fields: price, open, high, low, close, volume_24h, change_pct_1h,
#          change_pct_24h, change_pct_7d, market_cap, funding_rate

market_data,exchange=binance,symbol=BTC/USDT,asset_type=crypto price=67234.50,volume_24h=28500000000,change_pct_1h=0.45,change_pct_24h=2.3,change_pct_7d=-1.2,market_cap=1320000000000 1707753600000000000

market_data,exchange=yahoo,symbol=AAPL,asset_type=stock price=185.42,volume_24h=52000000,change_pct_24h=1.1 1707753600000000000

market_data,exchange=yahoo,symbol=EUR/USD,asset_type=forex price=1.0823,change_pct_24h=-0.15 1707753600000000000
```

### Sources de données

#### Binance WebSocket (crypto, temps réel)
```python
# Souscrit aux streams de prix pour chaque asset crypto
# URI: wss://stream.binance.com:9443/ws/{symbol}@ticker

# Données reçues:
# - Prix actuel (c)
# - Open 24h (o), High 24h (h), Low 24h (l)
# - Volume 24h (v)
# - Variation % 24h (P)
```

**Rate limits** : pas de limite sur les WebSocket streams
**Reconnexion** : auto-reconnect avec backoff exponentiel (1s, 2s, 4s, 8s, max 60s)
**API Key** : optionnelle pour les données publiques

#### Yahoo Finance (stocks, forex, indices)
```python
# Polling REST toutes les 15 secondes
# Utilise la librairie yfinance

# Assets supportés:
# - Actions US/EU: AAPL, MSFT, TSLA, etc.
# - Indices: ^GSPC (S&P500), ^IXIC (NASDAQ), ^FCHI (CAC40), ^GDAXI (DAX)
# - Forex: EURUSD=X, GBPUSD=X, USDJPY=X
# - Commodités: GC=F (Or), CL=F (Pétrole), SI=F (Argent)
```

**Rate limits** : ~2000 requêtes/heure (non officiel)
**API Key** : non requise
**Fallback** : Alpha Vantage si Yahoo tombe

#### CoinGecko (market cap, données enrichies)
```python
# Polling REST toutes les 60 secondes
# Endpoint: /api/v3/coins/markets

# Données enrichies:
# - Market cap
# - Market cap rank
# - Circulating supply
# - ATH (All-Time High) et distance
# - Variation 7d
```

**Rate limits** : 30 req/min (gratuit), 500 req/min (pro)
**API Key** : optionnelle (gratuit = 30 req/min)

### Gestion des erreurs

| Erreur | Action | Retry |
|--------|--------|-------|
| WebSocket déconnecté | Reconnexion auto | Backoff exponentiel |
| API timeout | Skip ce cycle | Prochain cycle normal |
| Rate limit atteint | Pause 60s | Auto-resume |
| API key invalide | Log erreur | Stop le source concerné |
| InfluxDB down | Buffer en mémoire (max 1000 points) | Retry toutes les 10s |
| Donnée malformée | Log + skip | Continue |

### Health Check

```python
# GET http://localhost:8080/health
# Réponse:
{
    "status": "healthy",
    "sources": {
        "binance_ws": {"connected": true, "last_data": "2s ago"},
        "yahoo_finance": {"connected": true, "last_data": "12s ago"},
        "coingecko": {"connected": true, "last_data": "45s ago"}
    },
    "influxdb": {"connected": true, "write_errors_1h": 0},
    "assets_tracked": 23,
    "uptime": "4h 23m"
}
```

---

## 2. News Feeder

### Rôle
Collecte les actualités financières et crypto, analyse le sentiment, et stocke dans InfluxDB.

### Structure des fichiers
```
collectors/news-feeder/
├── Dockerfile
├── requirements.txt
├── main.py
├── config.py
├── sources/
│   ├── __init__.py
│   ├── cryptopanic.py      # API CryptoPanic
│   ├── newsapi.py          # NewsAPI.org
│   └── rss_parser.py       # Flux RSS custom
├── processors/
│   ├── __init__.py
│   ├── sentiment.py        # Analyse de sentiment
│   ├── tagger.py           # Tag par asset mentionné
│   └── deduplicator.py     # Évite les doublons
├── writers/
│   ├── __init__.py
│   └── influxdb_writer.py
└── tests/
    └── test_sentiment.py
```

### Dépendances (requirements.txt)
```
influxdb-client==1.40.0
aiohttp==3.9.0
python-dotenv==1.0.0
pydantic==2.6.0
feedparser==6.0.11
vaderSentiment==3.3.2
textblob==0.18.0
beautifulsoup4==4.12.3
```

### Format de données

```
# Measurement: news_articles
# Tags: source, category, related_asset, sentiment_label
# Fields: title, url, sentiment_score, summary

news_articles,source=cryptopanic,category=crypto,related_asset=BTC,sentiment_label=positive title="Bitcoin breaks through resistance level",url="https://example.com/article",sentiment_score=0.72 1707753600000000000
```

### Analyse de sentiment

L'analyse utilise VADER (Valence Aware Dictionary and sEntiment Reasoner), optimisé pour les textes courts et les réseaux sociaux.

```python
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def analyze_sentiment(title: str) -> dict:
    scores = analyzer.polarity_scores(title)
    compound = scores['compound']

    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    return {
        "score": compound,       # -1.0 à +1.0
        "label": label           # positive/negative/neutral
    }
```

**Mapping label → icône Grafana** :
- `positive` (score > 0.05) → 🟢
- `neutral` (-0.05 à 0.05) → 🟡
- `negative` (score < -0.05) → 🔴

### Sources

#### CryptoPanic
```
API: https://cryptopanic.com/api/v1/posts/
Fréquence: toutes les 2 minutes
Données: titre, source, URL, timestamp, currencies mentionnées
Filtres: kind=news, filter=hot (populaires)
```

#### NewsAPI
```
API: https://newsapi.org/v2/everything
Fréquence: toutes les 5 minutes
Requêtes: "bitcoin OR ethereum OR crypto OR stock market"
Langue: en,fr
```

#### RSS Feeds
```
Feeds configurables dans .env ou PostgreSQL :
- https://feeds.bloomberg.com/markets/news.rss
- https://www.coindesk.com/arc/outboundfeeds/rss/
- Custom feeds ajoutés par l'utilisateur
Fréquence: toutes les 5 minutes
```

### Déduplication

Chaque article est identifié par un hash SHA256 de `source + titre + date`. Les doublons sont ignorés automatiquement.

---

## 3. Watchlist Manager (FastAPI)

### Rôle
API REST pour gérer les watchlists dynamiques. Permet à chaque utilisateur de définir ses propres listes d'assets à suivre.

### Structure des fichiers
```
collectors/watchlist-manager/
├── Dockerfile
├── requirements.txt
├── main.py                 # Point d'entrée FastAPI
├── config.py
├── models/
│   ├── __init__.py
│   ├── watchlist.py        # Modèles Pydantic
│   └── database.py         # Connexion PostgreSQL
├── routes/
│   ├── __init__.py
│   ├── watchlists.py       # CRUD watchlists
│   ├── assets.py           # Recherche d'assets
│   └── health.py           # Health check
├── services/
│   ├── __init__.py
│   └── asset_resolver.py   # Résolution symbol → exchange
└── tests/
    └── test_watchlists.py
```

### Dépendances (requirements.txt)
```
fastapi==0.109.0
uvicorn==0.27.0
sqlalchemy==2.0.25
asyncpg==0.29.0
python-dotenv==1.0.0
pydantic==2.6.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

### Endpoints API

Voir [API.md](API.md) pour la documentation complète.

Résumé :
```
GET    /health                          # Health check
GET    /api/v1/watchlists/{user_id}     # Lister les watchlists d'un user
POST   /api/v1/watchlists               # Créer une watchlist
PUT    /api/v1/watchlists/{id}          # Modifier une watchlist
DELETE /api/v1/watchlists/{id}          # Supprimer une watchlist
GET    /api/v1/assets/search?q=bitcoin  # Rechercher un asset
GET    /api/v1/assets/active            # Assets actuellement suivis
```

### Interaction avec les feeders

Quand une watchlist est modifiée, le Watchlist Manager notifie le Market Feeder pour qu'il ajuste les assets collectés :

```python
# Pseudo-code de notification
async def on_watchlist_change(watchlist_id: int):
    # 1. Récupérer tous les assets actifs (union de toutes les watchlists)
    active_assets = await get_all_active_assets()

    # 2. Écrire la liste dans un fichier partagé ou Redis
    # Le Market Feeder poll cette liste toutes les 30 secondes
    await update_active_assets_file(active_assets)
```

---

## Variables d'environnement communes

| Variable | Service | Description |
|----------|---------|-------------|
| `INFLUXDB_URL` | Market, News | `http://bloomberg-influxdb:8086` |
| `INFLUXDB_TOKEN` | Market, News | Token admin InfluxDB |
| `INFLUXDB_ORG` | Market, News | `bloomberg` |
| `POSTGRES_URL` | Market, Watchlist | Connection string PostgreSQL |
| `BINANCE_API_KEY` | Market | Clé API Binance (optionnel) |
| `BINANCE_SECRET` | Market | Secret Binance (optionnel) |
| `COINGECKO_API_KEY` | Market | Clé CoinGecko (optionnel) |
| `NEWSAPI_KEY` | News | Clé NewsAPI |
| `CRYPTOPANIC_TOKEN` | News | Token CryptoPanic |
| `JWT_SECRET` | Watchlist | Secret pour les JWT tokens |
| `LOG_LEVEL` | Tous | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Monitoring des collectors

Chaque collector expose un endpoint `/health` ou `/metrics` que Prometheus peut scraper :

```yaml
# Dans prometheus.yml
- job_name: 'market-feeder'
  static_configs:
    - targets: ['bloomberg-market-feeder:8080']
  metrics_path: '/metrics'

- job_name: 'watchlist-api'
  static_configs:
    - targets: ['bloomberg-watchlist-api:8000']
  metrics_path: '/metrics'
```

## Développement local

```bash
# Installer les dépendances en local (sans Docker)
cd collectors/market-feeder
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Lancer avec les variables d'env locales
export INFLUXDB_URL=http://localhost:8086
export INFLUXDB_TOKEN=mon-token-local
python main.py

# Tests
pytest tests/ -v
```
