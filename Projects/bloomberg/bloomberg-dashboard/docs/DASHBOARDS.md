# Spécifications Dashboards Bloomberg

> Design détaillé de chaque panel, requêtes Flux, et configuration Grafana.

## Thème Bloomberg

### Palette de couleurs

| Élément | Hex | Usage |
|---------|-----|-------|
| Background principal | `#0a0a0a` | Fond des dashboards |
| Background panel | `#111111` | Fond des panels individuels |
| Bordure panel | `#1a1a2e` | Séparation visuelle |
| Orange Bloomberg | `#ff8c00` | Titres, ticker, accents |
| Vert gain | `#00d4aa` | Variations positives |
| Rouge perte | `#ff3b3b` | Variations négatives |
| Texte principal | `#e0e0e0` | Données, labels |
| Texte secondaire | `#888888` | Métadonnées, timestamps |
| Jaune alerte | `#ffd700` | Warnings, alertes modérées |
| Bleu info | `#4a9eff` | Liens, infos complémentaires |

### Typographie

- **Police principale** : IBM Plex Mono (monospace)
- **Tailles** :
  - Prix principal : 32px bold
  - Variation % : 18px bold
  - Labels : 12px regular
  - Ticker défilant : 14px bold

### Configuration grafana.ini

```ini
[dashboards]
default_home_dashboard_path = /etc/grafana/dashboards-json/bloomberg-home.json

[unified_alerting]
enabled = true

[users]
default_theme = dark

[auth]
disable_login_form = false

[panels]
disable_sanitize_html = true
```

Le CSS custom est injecté via le plugin `marcusolsson-dynamictext-panel` avec du HTML/CSS inline dans les panels texte.

---

## Dashboard Principal — "Bloomberg Home"

### Layout (résolution 1920x1080)

```
┌──────────────────────────────────────────────────────────────────────┐
│  🔴 TICKER BAND — scroll horizontal automatique (hauteur: 50px)     │
│  BTC $67,234 ▲+2.3% │ ETH $3,456 ▼-0.8% │ S&P500 5,021 ▲+0.4%   │
├────────────────────────────────┬─────────────────────────────────────┤
│                                │                                     │
│   📈 CHART PRINCIPAL           │   📊 MARKET OVERVIEW GRID           │
│   Candlestick de $asset        │   Mini-cards 4x3 avec               │
│   avec SMA 20/50               │   prix + variation + sparkline      │
│   Hauteur: 400px               │   Hauteur: 400px                    │
│   Largeur: 60%                 │   Largeur: 40%                      │
│                                │                                     │
├────────────────────────────────┼──────────────┬──────────────────────┤
│                                │              │                      │
│   📰 NEWS FEED                 │  ⚡ ALERTES   │  🖥️ INFRA STATUS     │
│   Dernières news avec          │  Dernières   │  CPU, RAM, Disk      │
│   sentiment coloré             │  alertes     │  Container status    │
│   Hauteur: 300px               │  déclenchées │  Uptime              │
│   Largeur: 50%                 │  25%         │  25%                 │
│                                │              │                      │
├────────────────────────────────┴──────────────┴──────────────────────┤
│  ⏰ CLOCKS: New York │ London │ Paris │ Tokyo │ Sydney               │
└──────────────────────────────────────────────────────────────────────┘
```

### Variables Grafana (template variables)

```yaml
# Variable $asset — dropdown d'assets
name: asset
type: query
datasource: PostgreSQL
query: |
  SELECT DISTINCT unnest(assets)::text AS __text,
         unnest(assets)::text AS __value
  FROM watchlists
  WHERE user_id = $user_id
  ORDER BY __text
refresh: on_time_range_change
multi: false
include_all: false
default: BTC/USDT

# Variable $timeframe
name: timeframe
type: custom
values: 1m,5m,15m,1h,4h,1d
default: 1h

# Variable $exchange
name: exchange
type: custom
values: binance,yahoo,coingecko,all
default: all

# Variable $watchlist
name: watchlist
type: query
datasource: PostgreSQL
query: |
  SELECT name AS __text, id AS __value
  FROM watchlists
  WHERE user_id = $user_id
refresh: on_dashboard_load
```

---

### Panel 1 — Ticker Band (haut de page)

**Type** : `marcusolsson-dynamictext-panel`
**Hauteur** : 2 unités Grafana (≈50px)
**Largeur** : 24 colonnes (pleine largeur)

**Requête Flux** :
```flux
from(bucket: "markets")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "market_data")
  |> filter(fn: (r) => r._field == "price" or r._field == "change_pct_24h")
  |> last()
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> group()
  |> sort(columns: ["symbol"])
```

**Template HTML/CSS** :
```html
<style>
  .ticker-container {
    display: flex;
    overflow: hidden;
    white-space: nowrap;
    background: #0a0a0a;
    padding: 8px 0;
    font-family: 'IBM Plex Mono', monospace;
  }
  .ticker-scroll {
    display: flex;
    animation: scroll 30s linear infinite;
    gap: 40px;
  }
  @keyframes scroll {
    0% { transform: translateX(0); }
    100% { transform: translateX(-50%); }
  }
  .ticker-item {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .ticker-symbol { color: #ff8c00; font-weight: bold; font-size: 14px; }
  .ticker-price { color: #e0e0e0; font-size: 14px; }
  .ticker-change-up { color: #00d4aa; font-weight: bold; }
  .ticker-change-down { color: #ff3b3b; font-weight: bold; }
  .ticker-separator { color: #333; margin: 0 10px; }
</style>

<div class="ticker-container">
  <div class="ticker-scroll">
    {{#each data}}
    <div class="ticker-item">
      <span class="ticker-symbol">{{symbol}}</span>
      <span class="ticker-price">${{price}}</span>
      {{#if (gt change_pct_24h 0)}}
        <span class="ticker-change-up">▲+{{change_pct_24h}}%</span>
      {{else}}
        <span class="ticker-change-down">▼{{change_pct_24h}}%</span>
      {{/if}}
    </div>
    <span class="ticker-separator">│</span>
    {{/each}}
  </div>
</div>
```

**Rafraîchissement** : 5 secondes

---

### Panel 2 — Chart Principal (Candlestick)

**Type** : `natel-plotly-panel`
**Position** : gauche, sous le ticker
**Hauteur** : 16 unités (≈400px)
**Largeur** : 14 colonnes (60%)

**Requête Flux (OHLCV)** :
```flux
import "date"

from(bucket: "markets")
  |> range(start: -${timeframe_range})
  |> filter(fn: (r) => r._measurement == "market_data")
  |> filter(fn: (r) => r.symbol == "${asset}")
  |> filter(fn: (r) => r._field == "price")
  |> aggregateWindow(
      every: ${timeframe},
      fn: (tables=<-, column) => tables
        |> reduce(
            identity: {open: 0.0, high: -999999.0, low: 999999.0, close: 0.0, count: 0},
            fn: (r, accumulator) => ({
                open: if accumulator.count == 0 then r._value else accumulator.open,
                high: if r._value > accumulator.high then r._value else accumulator.high,
                low: if r._value < accumulator.low then r._value else accumulator.low,
                close: r._value,
                count: accumulator.count + 1
            })
        )
  )
```

**Trace Plotly** :
```json
{
  "type": "candlestick",
  "increasing": {"line": {"color": "#00d4aa"}},
  "decreasing": {"line": {"color": "#ff3b3b"}},
  "layout": {
    "paper_bgcolor": "#111111",
    "plot_bgcolor": "#111111",
    "font": {"color": "#e0e0e0", "family": "IBM Plex Mono"},
    "xaxis": {"gridcolor": "#1a1a2e", "showgrid": true},
    "yaxis": {"gridcolor": "#1a1a2e", "showgrid": true, "side": "right"}
  }
}
```

**Overlays (requêtes additionnelles)** :

SMA 20 :
```flux
from(bucket: "markets")
  |> range(start: -${timeframe_range})
  |> filter(fn: (r) => r._measurement == "market_data" and r.symbol == "${asset}" and r._field == "price")
  |> aggregateWindow(every: ${timeframe}, fn: mean)
  |> movingAverage(n: 20)
```

SMA 50 :
```flux
// Même requête avec movingAverage(n: 50)
```

Volume bars (panel séparé en dessous, hauteur 4 unités) :
```flux
from(bucket: "markets")
  |> range(start: -${timeframe_range})
  |> filter(fn: (r) => r._measurement == "market_data" and r.symbol == "${asset}" and r._field == "volume_24h")
  |> aggregateWindow(every: ${timeframe}, fn: mean)
```

---

### Panel 3 — Market Overview Grid

**Type** : `stat` panels en grille 4x3
**Position** : droite du chart principal
**Hauteur** : 16 unités (≈400px)
**Largeur** : 10 colonnes (40%)

Chaque cellule de la grille est un `stat` panel individuel :

**Requête Flux (par asset)** :
```flux
from(bucket: "markets")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "market_data")
  |> filter(fn: (r) => r.symbol == "BTC/USDT")  // changé par asset
  |> filter(fn: (r) => r._field == "price" or r._field == "change_pct_24h")
  |> last()
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
```

**Configuration du panel stat** :
```json
{
  "options": {
    "graphMode": "area",
    "colorMode": "background",
    "justifyMode": "auto",
    "textMode": "value_and_name",
    "orientation": "auto"
  },
  "fieldConfig": {
    "defaults": {
      "thresholds": {
        "steps": [
          {"color": "#ff3b3b", "value": null},
          {"color": "#ff3b3b", "value": -999},
          {"color": "#00d4aa", "value": 0}
        ]
      },
      "mappings": [],
      "unit": "currencyUSD",
      "decimals": 2
    }
  }
}
```

**Alternative dynamique** : utiliser un seul panel `marcusolsson-dynamictext-panel` avec une grille CSS pour afficher tous les assets d'une watchlist dynamiquement.

---

### Panel 4 — News Feed

**Type** : `marcusolsson-dynamictext-panel`
**Position** : bas gauche
**Hauteur** : 12 unités (≈300px)
**Largeur** : 12 colonnes (50%)

**Requête Flux** :
```flux
from(bucket: "news")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "news_articles")
  |> filter(fn: (r) => r._field == "title" or r._field == "url" or r._field == "sentiment_score" or r._field == "source")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 20)
```

**Template HTML** :
```html
<style>
  .news-container {
    font-family: 'IBM Plex Mono', monospace;
    max-height: 280px;
    overflow-y: auto;
  }
  .news-item {
    padding: 6px 10px;
    border-bottom: 1px solid #1a1a2e;
    display: flex;
    align-items: flex-start;
    gap: 8px;
  }
  .news-item:hover { background: #1a1a1a; }
  .news-sentiment { font-size: 16px; min-width: 20px; }
  .news-time { color: #888; font-size: 11px; min-width: 50px; }
  .news-title a { color: #e0e0e0; text-decoration: none; font-size: 12px; }
  .news-title a:hover { color: #ff8c00; }
  .news-source { color: #4a9eff; font-size: 10px; }
</style>

<div class="news-container">
  {{#each data}}
  <div class="news-item">
    <span class="news-sentiment">
      {{#if (gt sentiment_score 0.05)}}🟢
      {{else if (lt sentiment_score -0.05)}}🔴
      {{else}}🟡{{/if}}
    </span>
    <span class="news-time">{{formatTime _time "HH:mm"}}</span>
    <div>
      <div class="news-title"><a href="{{url}}" target="_blank">{{title}}</a></div>
      <span class="news-source">{{source}}</span>
    </div>
  </div>
  {{/each}}
</div>
```

---

### Panel 5 — Alertes récentes

**Type** : Table panel natif Grafana
**Position** : bas centre
**Hauteur** : 12 unités
**Largeur** : 6 colonnes (25%)

**Datasource** : Grafana Alerting (built-in)

Affiche les dernières alertes déclenchées avec colonnes : timestamp, asset, condition, valeur actuelle, statut (firing/resolved).

---

### Panel 6 — Infra Status

**Type** : `stat` + `gauge` panels
**Position** : bas droite
**Hauteur** : 12 unités
**Largeur** : 6 colonnes (25%)

**Requêtes Prometheus** :
```promql
# CPU Usage (%)
100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# RAM Usage (%)
(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100

# Disk Usage (%)
(1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100

# Container count running
count(container_last_seen{name=~"bloomberg.*"})
```

---

### Panel 7 — Horloges multi-timezone

**Type** : `grafana-clock-panel` (5 instances)
**Position** : barre inférieure
**Hauteur** : 3 unités (≈50px)

| Instance | Timezone | Label |
|----------|----------|-------|
| 1 | America/New_York | NEW YORK |
| 2 | Europe/London | LONDON |
| 3 | Europe/Paris | PARIS |
| 4 | Asia/Tokyo | TOKYO |
| 5 | Australia/Sydney | SYDNEY |

---

## Dashboard "Deep Dive"

Dashboard détaillé pour un seul asset, accessible via clic sur le Market Overview Grid.

### Layout
```
┌──────────────────────────────────────────────────────────────┐
│  HEADER: $asset — $exchange — Prix actuel — Variation 24h    │
├──────────────────────────┬───────────────────────────────────┤
│  Chart Candlestick 1h    │  Chart Candlestick 15m            │
│  (avec SMA, Bollinger)   │  (zoom court terme)               │
├──────────────────────────┼───────────────────────────────────┤
│  Volume Profile          │  Corrélation avec BTC             │
├──────────────────────────┼───────────────────────────────────┤
│  News filtrées par asset │  Métriques clés                   │
│                          │  (Market Cap, Supply, ATH, etc.)  │
└──────────────────────────┴───────────────────────────────────┘
```

## Dashboard "Portfolio"

Suivi du P&L et de l'allocation.

### Layout
```
┌──────────────────────────────────────────────────────────────┐
│  HEADER: P&L Total — Valeur portefeuille — Performance %     │
├──────────────────────────┬───────────────────────────────────┤
│  Performance historique  │  Allocation (Pie chart)            │
│  (line chart)            │                                    │
├──────────────────────────┼───────────────────────────────────┤
│  P&L par asset (table)   │  Drawdown historique              │
│  avec tri par perf       │                                    │
└──────────────────────────┴───────────────────────────────────┘
```

## Dashboard "Infra Monitor"

Monitoring complet de l'infrastructure.

### Layout
```
┌──────────────────────────────────────────────────────────────┐
│  CPU (graph) │ RAM (graph) │ Disk I/O (graph) │ Network      │
├──────────────────────────────────────────────────────────────┤
│  Container status (table): name, CPU%, RAM, uptime, restarts │
├──────────────────────────┬───────────────────────────────────┤
│  API latencies           │  Collector health checks           │
│  (heatmap)               │  (stat panels vert/rouge)          │
├──────────────────────────┼───────────────────────────────────┤
│  Logs récents (Loki)     │  Alertes infra actives             │
└──────────────────────────┴───────────────────────────────────┘
```

## Provisioning des dashboards

Les dashboards sont provisionnés automatiquement au démarrage de Grafana.

**Fichier** : `grafana/provisioning/dashboards/default.yml`
```yaml
apiVersion: 1

providers:
  - name: 'Bloomberg Dashboards'
    orgId: 1
    folder: 'Bloomberg'
    type: file
    disableDeletion: false
    editable: true
    updateIntervalSeconds: 30
    allowUiUpdates: true
    options:
      path: /etc/grafana/dashboards-json
      foldersFromFilesStructure: false
```

Les fichiers JSON des dashboards sont dans `grafana/dashboards-json/` :
- `bloomberg-home.json` — Dashboard principal
- `bloomberg-deep-dive.json` — Vue détaillée asset
- `bloomberg-portfolio.json` — Portfolio tracker
- `bloomberg-infra.json` — Monitoring infrastructure

## Kiosk Mode (affichage TV)

Pour un affichage permanent sur un écran dédié :

```
https://ton-domaine.com/d/bloomberg-home?orgId=1&kiosk=tv&refresh=5s
```

Paramètres :
- `kiosk=tv` : masque la sidebar et le header Grafana
- `refresh=5s` : rafraîchissement automatique toutes les 5 secondes
- Playlist : configurer une playlist Grafana pour rotation entre dashboards
