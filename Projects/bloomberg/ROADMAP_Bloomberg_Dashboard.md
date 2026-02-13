# 🖥️ ROADMAP — Bloomberg-Style Grafana Dashboard

> **Projet** : Dashboard multi-usage style terminal Bloomberg, fully customisable
> **Stack** : Grafana + Docker + APIs marchés + InfluxDB + Prometheus
> **Équipe** : 2-5 personnes | **Mode** : Sprint full-time (1-2 semaines)
> **Départ** : From scratch sur VPS dédié

---

## 📐 Architecture Cible

```
┌─────────────────────────────────────────────────────────────────┐
│                    VPS DÉDIÉ (Ubuntu 22.04+)                    │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │   GRAFANA    │  │   NGINX      │  │   ALERTMANAGER        │  │
│  │   (port 3000)│  │   Reverse    │  │   + Telegram Bot      │  │
│  │   + Plugins  │  │   Proxy +SSL │  │   + Email SMTP        │  │
│  └──────┬───────┘  └──────────────┘  └───────────────────────┘  │
│         │                                                       │
│  ┌──────┴───────────────────────────────────────────────────┐   │
│  │                   DATA LAYER                              │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │   │
│  │  │ InfluxDB   │  │ PostgreSQL │  │ Prometheus         │  │   │
│  │  │ (time-     │  │ (config,   │  │ (métriques infra)  │  │   │
│  │  │  series)   │  │  users,    │  │ + Node Exporter    │  │   │
│  │  │            │  │  watchlists)│  │ + cAdvisor         │  │   │
│  │  └────────────┘  └────────────┘  └────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 COLLECTORS / FEEDERS                       │   │
│  │  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────────┐  │   │
│  │  │ Market  │ │ News     │ │ Infra   │ │ Custom       │  │   │
│  │  │ Feeder  │ │ Feeder   │ │ Monitor │ │ Watchlist    │  │   │
│  │  │ (Python)│ │ (Python) │ │ (Prom.) │ │ Manager      │  │   │
│  │  └─────────┘ └──────────┘ └─────────┘ └──────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  EXTERNAL APIs                            │   │
│  │  Binance │ CoinGecko │ Yahoo Finance │ Alpha Vantage     │   │
│  │  NewsAPI │ CryptoPanic │ RSS Feeds │ Exchange Rates API  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗓️ PHASE 0 — Fondations (Jour 1)

> Mise en place du VPS et de l'environnement Docker complet.

- [ ] **Provisionner le VPS**
  - Ubuntu 22.04 LTS, minimum 4 vCPU / 8 GB RAM / 80 GB SSD
  - Configurer SSH keys, firewall (UFW), fail2ban
  - Créer un user non-root dédié au projet

- [ ] **Installer Docker & Docker Compose**
  - Docker Engine 24+
  - Docker Compose v2
  - Vérifier avec `docker run hello-world`

- [ ] **Structurer le repo projet**
  ```
  bloomberg-dashboard/
  ├── docker-compose.yml
  ├── .env
  ├── grafana/
  │   ├── provisioning/
  │   │   ├── datasources/
  │   │   ├── dashboards/
  │   │   └── alerting/
  │   ├── dashboards-json/
  │   └── grafana.ini
  ├── collectors/
  │   ├── market-feeder/
  │   ├── news-feeder/
  │   └── watchlist-manager/
  ├── nginx/
  │   └── nginx.conf
  ├── prometheus/
  │   └── prometheus.yml
  └── scripts/
      └── setup.sh
  ```

- [ ] **Créer le `docker-compose.yml` de base**
  - Services : grafana, influxdb, postgres, prometheus, nginx
  - Volumes persistants pour toutes les BDD
  - Réseau interne `bloomberg-net`

- [ ] **Premier lancement** — vérifier que tous les containers tournent

📊 **Critère de validation** : `docker ps` montre 5 containers healthy

---

## 🗓️ PHASE 1 — Data Layer (Jours 2-3)

> Mettre en place les bases de données et les premiers flux de données.

### 1.1 — InfluxDB (Time-Series)

- [ ] Configurer InfluxDB 2.x avec organisation + bucket `markets`
- [ ] Créer les buckets :
  - `markets` — prix, volumes, order books
  - `news` — articles, sentiment scores
  - `infra` — métriques système (backup Prometheus)
  - `custom` — données utilisateur personnalisées
- [ ] Configurer les retention policies (7j raw, 30j downsampled, 1y aggregated)
- [ ] Tester l'écriture avec un point de donnée factice

### 1.2 — PostgreSQL (Config & Users)

- [ ] Créer la BDD `bloomberg_config`
- [ ] Tables à créer :
  ```sql
  -- Watchlists dynamiques
  CREATE TABLE watchlists (
    id SERIAL PRIMARY KEY,
    user_id INT,
    name VARCHAR(100),
    assets JSONB,        -- ["BTC/USDT", "ETH/USDT", "AAPL"]
    created_at TIMESTAMP DEFAULT NOW()
  );

  -- Configuration des panels par user
  CREATE TABLE user_layouts (
    id SERIAL PRIMARY KEY,
    user_id INT,
    layout_name VARCHAR(100),
    panels_config JSONB,  -- config Grafana des panels
    is_default BOOLEAN DEFAULT false
  );

  -- Alertes custom
  CREATE TABLE alert_rules (
    id SERIAL PRIMARY KEY,
    user_id INT,
    asset VARCHAR(50),
    condition VARCHAR(20),  -- 'above', 'below', 'pct_change'
    threshold DECIMAL,
    channel VARCHAR(20),    -- 'telegram', 'email', 'webhook'
    active BOOLEAN DEFAULT true
  );
  ```
- [ ] Ajouter des données de test

### 1.3 — Prometheus (Monitoring Infra)

- [ ] Configurer `prometheus.yml` avec targets :
  - Node Exporter (métriques VPS)
  - cAdvisor (métriques containers Docker)
  - Grafana self-monitoring
  - InfluxDB health
- [ ] Vérifier la collecte sur `http://localhost:9090/targets`

📊 **Critère de validation** : Grafana se connecte aux 3 datasources sans erreur

---

## 🗓️ PHASE 2 — Collectors & Feeders (Jours 3-5)

> Scripts Python qui alimentent les BDD en données temps réel.

### 2.1 — Market Feeder (Priorité haute)

- [ ] **Script Python `market_feeder.py`**
  - Connexion WebSocket Binance pour les données temps réel
  - Fallback REST API pour les données historiques
  - Support multi-exchange (Binance, Bybit, Kraken via ccxt)
  - Écriture dans InfluxDB toutes les 1-5 secondes

- [ ] **Données collectées par asset :**
  - Prix (open, high, low, close)
  - Volume 24h
  - Variation % (1h, 24h, 7d)
  - Market cap (via CoinGecko)
  - Funding rate (pour les futures)

- [ ] **Support Forex & Actions** (via Yahoo Finance / Alpha Vantage)
  - Polling toutes les 15-60 secondes
  - Indices : S&P 500, NASDAQ, CAC 40, DAX
  - Commodités : Or, Pétrole, Argent

- [ ] **Watchlist Manager**
  - API REST (FastAPI) pour CRUD watchlists
  - Le feeder ne collecte que les assets dans les watchlists actives
  - Endpoint : `POST /watchlist`, `GET /watchlist/{user_id}`

- [ ] Dockeriser dans `collectors/market-feeder/Dockerfile`

### 2.2 — News Feeder

- [ ] **Script Python `news_feeder.py`**
  - Sources : CryptoPanic API, NewsAPI, RSS Feeds custom
  - Polling toutes les 2-5 minutes
  - Extraction : titre, source, URL, timestamp, tags, sentiment

- [ ] **Analyse de sentiment basique**
  - TextBlob ou VADER pour un score -1 à +1
  - Tag par asset mentionné dans le titre/corps
  - Stockage dans InfluxDB bucket `news`

- [ ] Dockeriser dans `collectors/news-feeder/Dockerfile`

### 2.3 — Tests d'intégration

- [ ] Vérifier le flux complet : API → Collector → InfluxDB → Grafana
- [ ] Monitorer les erreurs et les latences
- [ ] Ajouter des health checks dans docker-compose

📊 **Critère de validation** : Données en temps réel visibles dans Grafana Explore

---

## 🗓️ PHASE 3 — Dashboard Bloomberg Core (Jours 5-8)

> Construction des dashboards Grafana avec l'esthétique Bloomberg.

### 3.1 — Thème Bloomberg Dark

- [ ] **Personnaliser `grafana.ini`**
  ```ini
  [unified_alerting]
  enabled = true

  [dashboards]
  default_home_dashboard_path = /etc/grafana/dashboards-json/home.json

  [auth]
  disable_login_form = false
  ```

- [ ] **Thème CSS custom** (via plugin `grafana-custom-css` ou injection)
  - Background : `#0a0a0a` (noir profond Bloomberg)
  - Texte principal : `#ff8c00` (orange Bloomberg)
  - Texte secondaire : `#00d4aa` (vert gain) / `#ff3b3b` (rouge perte)
  - Bordures panels : `#1a1a2e`
  - Police : `Consolas` ou `IBM Plex Mono`

- [ ] **Variables Grafana globales** (template variables)
  - `$asset` — dropdown avec les assets de la watchlist active
  - `$timeframe` — 1m, 5m, 15m, 1h, 4h, 1d
  - `$exchange` — Binance, Bybit, Yahoo, etc.
  - `$user` — pour filtrer par utilisateur
  - `$watchlist` — sélection de watchlist

### 3.2 — Panels Bloomberg (Dashboard Principal)

- [ ] **🔴 Ticker Band (haut de page)**
  - Plugin : `marcusolsson-dynamictext-panel`
  - Bandeau horizontal avec scroll automatique
  - Format : `BTC $67,234 ▲+2.3% | ETH $3,456 ▼-0.8% | ...`
  - Couleur dynamique vert/rouge selon variation

- [ ] **📊 Market Overview Grid (centre)**
  - Layout 4x3 ou 6x4 panels
  - Chaque cellule = 1 asset avec :
    - Nom + Logo
    - Prix actuel (gros)
    - Variation % colorée
    - Mini sparkline 24h
  - Plugin : `stat panel` + `sparkline`

- [ ] **📈 Chart Principal (gauche, grand)**
  - Candlestick chart pour l'asset sélectionné
  - Plugin : `natel-plotly-panel` ou `marcusolsson-dynamictext-panel`
  - Timeframe dynamique via variable `$timeframe`
  - Overlays : SMA 20, SMA 50, Volume bars

- [ ] **📰 News Feed (droite)**
  - Liste scrollable des dernières news
  - Plugin : `marcusolsson-dynamictext-panel`
  - Icône sentiment (🟢🟡🔴)
  - Clic → ouvre l'article source
  - Filtre par asset sélectionné

- [ ] **⚡ Alertes & Événements (bas)**
  - Panel table avec les dernières alertes déclenchées
  - Colonnes : timestamp, asset, condition, valeur, statut
  - Tri par date décroissante

- [ ] **🖥️ Infra Status (coin inférieur droit)**
  - Mini gauges : CPU, RAM, Disk, Network
  - Statut des containers Docker
  - Uptime du système

### 3.3 — Dashboards Secondaires

- [ ] **Dashboard "Deep Dive"**
  - Vue détaillée d'un seul asset
  - Order book (si dispo), chart multi-timeframe
  - Corrélations avec autres assets
  - Volume profile

- [ ] **Dashboard "Portfolio"**
  - P&L total, par asset
  - Allocation pie chart
  - Performance historique
  - Drawdown max

- [ ] **Dashboard "Infra Monitor"**
  - Métriques Prometheus complètes
  - Logs des collectors
  - Santé des API externes
  - Latences réseau

📊 **Critère de validation** : Dashboard principal fonctionnel avec données live, navigable par toute l'équipe

---

## 🗓️ PHASE 4 — Customisation Avancée (Jours 8-10)

> Rendre le tout modulaire et personnalisable par chaque utilisateur.

### 4.1 — Système de Layouts

- [ ] **Créer des playlists Grafana** pour rotation auto entre dashboards
- [ ] **Dashboard links** pour navigation fluide entre vues
- [ ] **Kiosk mode** pour affichage TV / écran dédié
- [ ] **Exporter les dashboards en JSON** pour backup/partage

### 4.2 — Watchlists Dynamiques

- [ ] **API FastAPI complète**
  ```
  GET    /api/watchlists/{user_id}
  POST   /api/watchlists
  PUT    /api/watchlists/{id}
  DELETE /api/watchlists/{id}
  GET    /api/assets/search?q=bitcoin
  ```
- [ ] **Variable Grafana connectée à PostgreSQL**
  - Query : `SELECT unnest(assets) FROM watchlists WHERE user_id = $user`
  - Mise à jour automatique quand la watchlist change

### 4.3 — Alerting Multi-Canal

- [ ] **Grafana Alerting natif**
  - Rules sur les métriques InfluxDB
  - Conditions : prix > seuil, variation % > X, volume spike

- [ ] **Contact Points configurés :**
  - Telegram Bot → channel d'équipe
  - Email SMTP (via Mailgun ou Brevo)
  - Webhook générique (Discord, Slack, custom)

- [ ] **Notification templates** Bloomberg-style :
  ```
  🚨 ALERT: BTC/USDT
  Price: $67,500 (+3.2% in 1h)
  Condition: Above $67,000
  Time: 2026-02-12 14:32 UTC
  ```

### 4.4 — Multi-Thèmes

- [ ] Thème "Bloomberg Classic" (noir + orange)
- [ ] Thème "Bloomberg Light" (blanc + bleu marine)
- [ ] Thème "Trading Dark" (noir + vert néon)
- [ ] Switch de thème via variable Grafana ou CSS toggle

📊 **Critère de validation** : Chaque membre de l'équipe peut créer sa watchlist et recevoir ses alertes

---

## 🗓️ PHASE 5 — Sécurité & Production (Jours 10-12)

> Hardening, SSL, auth, backups — prêt pour la prod.

### 5.1 — Reverse Proxy & SSL

- [ ] **Nginx configuration**
  - Reverse proxy vers Grafana
  - SSL via Let's Encrypt (Certbot)
  - Rate limiting
  - Headers de sécurité (HSTS, CSP, X-Frame-Options)

- [ ] **Domaine** : configurer DNS A record vers le VPS

### 5.2 — Authentification & Rôles

- [ ] **Grafana auth**
  - Organisations par équipe
  - Rôles : Admin, Editor, Viewer
  - OAuth (optionnel) : GitHub, Google

- [ ] **API auth** (pour le Watchlist Manager)
  - JWT tokens
  - Rate limiting par user

### 5.3 — Backups & Monitoring

- [ ] **Backup automatisé** (cron daily)
  - Dump PostgreSQL
  - Backup InfluxDB
  - Export dashboards Grafana JSON
  - Upload vers S3 ou stockage externe

- [ ] **Monitoring du monitoring**
  - Alertes si un collector crash
  - Alertes si InfluxDB/Postgres down
  - Dead man's switch (heartbeat)

### 5.4 — Performance Tuning

- [ ] Optimiser les requêtes InfluxDB (Flux queries)
- [ ] Configurer le cache Grafana
- [ ] Limiter la rétention des données haute fréquence
- [ ] Tester la charge avec 5 users simultanés

📊 **Critère de validation** : Dashboard accessible en HTTPS, auth fonctionnelle, backups quotidiens

---

## 🗓️ PHASE 6 — Polish & Documentation (Jours 12-14)

> Finitions, documentation, onboarding de l'équipe.

### 6.1 — UX Polish

- [ ] Ajuster les tailles de police pour la lisibilité
- [ ] Harmoniser les couleurs entre tous les panels
- [ ] Ajouter des annotations Grafana pour les événements majeurs
- [ ] Tester le responsive (mobile / tablette)
- [ ] Configurer le rafraîchissement auto optimal (5s ticker, 30s charts)

### 6.2 — Documentation

- [ ] **README.md** du repo avec setup instructions
- [ ] **Guide utilisateur** : comment utiliser le dashboard
- [ ] **Guide admin** : comment ajouter des assets, configurer les alertes
- [ ] **Runbook** : que faire si un service tombe

### 6.3 — Onboarding Équipe

- [ ] Créer les comptes Grafana pour chaque membre
- [ ] Session de démo / walkthrough
- [ ] Chaque membre crée sa première watchlist
- [ ] Vérifier que les alertes arrivent bien

📊 **Critère de validation** : L'équipe utilise le dashboard de manière autonome

---

## 📦 Stack Technique Complète

| Composant | Technologie | Rôle |
|-----------|------------|------|
| Dashboard | **Grafana 11+** | Visualisation, alerting, UI |
| Time-Series DB | **InfluxDB 2.x** | Données marchés, news, custom |
| Relational DB | **PostgreSQL 16** | Config, users, watchlists |
| Monitoring | **Prometheus** | Métriques infra + containers |
| Collectors | **Python 3.11+** | Market feeder, news feeder |
| API Custom | **FastAPI** | Watchlist CRUD, webhooks |
| Reverse Proxy | **Nginx** | SSL, routing, sécurité |
| Containerisation | **Docker Compose** | Orchestration de tous les services |
| Alerting | **Grafana + Telegram** | Notifications multi-canal |
| Scheduled Tasks | **Cron + Systemd** | Backups, maintenance |

---

## 🔌 Plugins Grafana Requis

| Plugin | Usage |
|--------|-------|
| `marcusolsson-dynamictext-panel` | Ticker défilant, news feed |
| `natel-plotly-panel` | Candlestick charts avancés |
| `grafana-clock-panel` | Horloges multi-timezone |
| `grafana-polystat-panel` | Vue hexagonale des assets |
| `grafana-worldmap-panel` | Carte des exchanges/marchés |
| `yesoreyeram-infinity-datasource` | Requêtes API REST directes |
| `marcusolsson-json-datasource` | Parsing JSON custom |

---

## ⏱️ Planning Résumé

```
Jour  1      │████████│ Phase 0 — Fondations (VPS, Docker, structure)
Jours 2-3    │████████████████│ Phase 1 — Data Layer (InfluxDB, PG, Prometheus)
Jours 3-5    │████████████████████████│ Phase 2 — Collectors (Market, News, Watchlist)
Jours 5-8    │████████████████████████████████│ Phase 3 — Dashboard Bloomberg Core
Jours 8-10   │████████████████████████│ Phase 4 — Customisation avancée
Jours 10-12  │████████████████████████│ Phase 5 — Sécurité & Production
Jours 12-14  │████████████████████████│ Phase 6 — Polish & Documentation
```

---

## 🚀 Quick Wins (à faire en premier pour la motivation)

1. **Docker Compose up** → voir Grafana tourner (30 min)
2. **Un prix BTC live** dans Grafana via InfluxDB (1-2h)
3. **Le ticker défilant** avec 5 cryptos (2-3h)
4. **Le thème noir Bloomberg** appliqué (1h)

---

## 🔮 Évolutions Futures (Post-Sprint)

- [ ] Mode "TV Broadcast" avec rotation automatique entre dashboards
- [ ] App mobile (Grafana Mobile)
- [ ] Machine Learning : prédiction de tendances via TensorFlow Serving
- [ ] Social trading : partage de watchlists entre membres
- [ ] Intégration Freqtrade : P&L des bots de trading directement dans le dashboard
- [ ] Voice alerts via TTS (Text-to-Speech)
- [ ] Replay mode : rejouer les données historiques comme un magnétoscope

---

*Dernière mise à jour : 12 février 2026*
*Auteur : Antoine & Claude*
