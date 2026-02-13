# Configuration Docker

> Détails de chaque service Docker Compose et configuration.

## docker-compose.yml — Référence complète

Chaque service est préfixé `bloomberg-` pour éviter les conflits avec d'autres projets.

### Services et dépendances

```
bloomberg-nginx ─────────────────────────────► bloomberg-grafana
                                                     │
                                    ┌────────────────┼────────────────┐
                                    ▼                ▼                ▼
                          bloomberg-influxdb  bloomberg-postgres  bloomberg-prometheus
                                    ▲                ▲                ▲
                                    │                │                │
                          bloomberg-market-feeder     │    bloomberg-node-exporter
                          bloomberg-news-feeder       │    bloomberg-cadvisor
                                              bloomberg-watchlist-api
```

### Ordre de démarrage (depends_on)

1. `bloomberg-influxdb`, `bloomberg-postgres`, `bloomberg-prometheus` (bases de données)
2. `bloomberg-node-exporter`, `bloomberg-cadvisor` (monitoring agents)
3. `bloomberg-market-feeder`, `bloomberg-news-feeder`, `bloomberg-watchlist-api` (collectors)
4. `bloomberg-grafana` (dashboard)
5. `bloomberg-nginx` (reverse proxy)

## Configuration par service

### Grafana

```yaml
bloomberg-grafana:
  image: grafana/grafana:11.4.0
  container_name: bloomberg-grafana
  restart: unless-stopped
  init: true
  environment:
    - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER}
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
    - GF_INSTALL_PLUGINS=marcusolsson-dynamictext-panel,natel-plotly-panel,grafana-clock-panel,grafana-polystat-panel,yesoreyeram-infinity-datasource,marcusolsson-json-datasource
    - GF_SERVER_ROOT_URL=https://${DOMAIN}
    - GF_SERVER_SERVE_FROM_SUB_PATH=false
    - GF_UNIFIED_ALERTING_ENABLED=true
  volumes:
    - grafana-data:/var/lib/grafana
    - ./grafana/provisioning:/etc/grafana/provisioning:ro
    - ./grafana/dashboards-json:/etc/grafana/dashboards-json:ro
    - ./grafana/grafana.ini:/etc/grafana/grafana.ini:ro
  networks:
    - bloomberg-net
  deploy:
    resources:
      limits:
        cpus: "1.0"
        memory: 1G
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
  depends_on:
    bloomberg-influxdb:
      condition: service_healthy
    bloomberg-postgres:
      condition: service_healthy
    bloomberg-prometheus:
      condition: service_healthy
```

**Variables d'env requises** : `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`, `DOMAIN`

**Plugins installés automatiquement** :
| Plugin | Usage |
|--------|-------|
| `marcusolsson-dynamictext-panel` | Ticker, news feed |
| `natel-plotly-panel` | Candlestick charts |
| `grafana-clock-panel` | Horloges multi-timezone |
| `grafana-polystat-panel` | Vue hexagonale assets |
| `yesoreyeram-infinity-datasource` | Requêtes REST directes |
| `marcusolsson-json-datasource` | Parsing JSON |

---

### InfluxDB

```yaml
bloomberg-influxdb:
  image: influxdb:2.7
  container_name: bloomberg-influxdb
  restart: unless-stopped
  init: true
  environment:
    - DOCKER_INFLUXDB_INIT_MODE=setup
    - DOCKER_INFLUXDB_INIT_USERNAME=${INFLUXDB_USERNAME}
    - DOCKER_INFLUXDB_INIT_PASSWORD=${INFLUXDB_PASSWORD}
    - DOCKER_INFLUXDB_INIT_ORG=bloomberg
    - DOCKER_INFLUXDB_INIT_BUCKET=markets
    - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=${INFLUXDB_TOKEN}
    - DOCKER_INFLUXDB_INIT_RETENTION=168h  # 7 jours
  volumes:
    - influxdb-data:/var/lib/influxdb2
    - influxdb-config:/etc/influxdb2
  networks:
    - bloomberg-net
  deploy:
    resources:
      limits:
        cpus: "2.0"
        memory: 3G
  healthcheck:
    test: ["CMD", "influx", "ping"]
    interval: 30s
    timeout: 10s
    retries: 5
    start_period: 30s
```

**Variables d'env** : `INFLUXDB_USERNAME`, `INFLUXDB_PASSWORD`, `INFLUXDB_TOKEN`

**Buckets à créer après le premier démarrage** :
```bash
# Depuis le container
docker exec bloomberg-influxdb influx bucket create -n news -o bloomberg -r 2160h
docker exec bloomberg-influxdb influx bucket create -n infra -o bloomberg -r 360h
docker exec bloomberg-influxdb influx bucket create -n custom -o bloomberg -r 0
docker exec bloomberg-influxdb influx bucket create -n markets_5min -o bloomberg -r 720h
docker exec bloomberg-influxdb influx bucket create -n markets_1h -o bloomberg -r 8760h
```

---

### PostgreSQL

```yaml
bloomberg-postgres:
  image: postgres:16-alpine
  container_name: bloomberg-postgres
  restart: unless-stopped
  init: true
  environment:
    - POSTGRES_DB=bloomberg_config
    - POSTGRES_USER=${POSTGRES_USER}
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
  volumes:
    - postgres-data:/var/lib/postgresql/data
    - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql:ro
  networks:
    - bloomberg-net
  deploy:
    resources:
      limits:
        cpus: "0.5"
        memory: 512M
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d bloomberg_config"]
    interval: 30s
    timeout: 10s
    retries: 5
    start_period: 20s
```

**Variables d'env** : `POSTGRES_USER`, `POSTGRES_PASSWORD`

**Init automatique** : le fichier `scripts/init-db.sql` est exécuté au premier démarrage.

---

### Prometheus

```yaml
bloomberg-prometheus:
  image: prom/prometheus:v2.50.0
  container_name: bloomberg-prometheus
  restart: unless-stopped
  init: true
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.path=/prometheus'
    - '--storage.tsdb.retention.time=15d'
    - '--web.enable-lifecycle'
  volumes:
    - prometheus-data:/prometheus
    - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
  networks:
    - bloomberg-net
  deploy:
    resources:
      limits:
        cpus: "1.0"
        memory: 1G
  healthcheck:
    test: ["CMD", "wget", "--spider", "-q", "http://localhost:9090/-/healthy"]
    interval: 30s
    timeout: 10s
    retries: 3
```

---

### Market Feeder

```yaml
bloomberg-market-feeder:
  build:
    context: ./collectors/market-feeder
    dockerfile: Dockerfile
  container_name: bloomberg-market-feeder
  restart: unless-stopped
  init: true
  environment:
    - INFLUXDB_URL=http://bloomberg-influxdb:8086
    - INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
    - INFLUXDB_ORG=bloomberg
    - INFLUXDB_BUCKET=markets
    - POSTGRES_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@bloomberg-postgres:5432/bloomberg_config
    - BINANCE_API_KEY=${BINANCE_API_KEY}
    - BINANCE_SECRET=${BINANCE_SECRET}
    - YAHOO_FINANCE_ENABLED=true
    - COINGECKO_API_KEY=${COINGECKO_API_KEY}
    - COLLECTION_INTERVAL_WS=1
    - COLLECTION_INTERVAL_REST=15
    - LOG_LEVEL=INFO
  networks:
    - bloomberg-net
  deploy:
    resources:
      limits:
        cpus: "0.5"
        memory: 512M
  healthcheck:
    test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8080/health')"]
    interval: 60s
    timeout: 10s
    retries: 3
    start_period: 30s
  depends_on:
    bloomberg-influxdb:
      condition: service_healthy
    bloomberg-postgres:
      condition: service_healthy
```

---

### News Feeder

```yaml
bloomberg-news-feeder:
  build:
    context: ./collectors/news-feeder
    dockerfile: Dockerfile
  container_name: bloomberg-news-feeder
  restart: unless-stopped
  init: true
  environment:
    - INFLUXDB_URL=http://bloomberg-influxdb:8086
    - INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
    - INFLUXDB_ORG=bloomberg
    - INFLUXDB_BUCKET=news
    - NEWSAPI_KEY=${NEWSAPI_KEY}
    - CRYPTOPANIC_TOKEN=${CRYPTOPANIC_TOKEN}
    - POLLING_INTERVAL=120
    - SENTIMENT_ENABLED=true
    - LOG_LEVEL=INFO
  networks:
    - bloomberg-net
  deploy:
    resources:
      limits:
        cpus: "0.25"
        memory: 256M
  depends_on:
    bloomberg-influxdb:
      condition: service_healthy
```

---

### Watchlist Manager (FastAPI)

```yaml
bloomberg-watchlist-api:
  build:
    context: ./collectors/watchlist-manager
    dockerfile: Dockerfile
  container_name: bloomberg-watchlist-api
  restart: unless-stopped
  init: true
  environment:
    - POSTGRES_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@bloomberg-postgres:5432/bloomberg_config
    - JWT_SECRET=${JWT_SECRET}
    - LOG_LEVEL=INFO
  networks:
    - bloomberg-net
  deploy:
    resources:
      limits:
        cpus: "0.25"
        memory: 256M
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
  depends_on:
    bloomberg-postgres:
      condition: service_healthy
```

---

### Node Exporter & cAdvisor

```yaml
bloomberg-node-exporter:
  image: prom/node-exporter:v1.7.0
  container_name: bloomberg-node-exporter
  restart: unless-stopped
  command:
    - '--path.rootfs=/host'
  pid: host
  volumes:
    - '/:/host:ro,rslave'
  networks:
    - bloomberg-net
  deploy:
    resources:
      limits:
        cpus: "0.1"
        memory: 64M

bloomberg-cadvisor:
  image: gcr.io/cadvisor/cadvisor:v0.49.1
  container_name: bloomberg-cadvisor
  restart: unless-stopped
  volumes:
    - /:/rootfs:ro
    - /var/run:/var/run:ro
    - /sys:/sys:ro
    - /var/lib/docker/:/var/lib/docker:ro
    - /dev/disk/:/dev/disk:ro
  networks:
    - bloomberg-net
  deploy:
    resources:
      limits:
        cpus: "0.25"
        memory: 256M
```

---

### Nginx

```yaml
bloomberg-nginx:
  image: nginx:1.25-alpine
  container_name: bloomberg-nginx
  restart: unless-stopped
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./nginx/ssl:/etc/nginx/ssl:ro
    - certbot-data:/var/www/certbot:ro
  networks:
    - bloomberg-net
  deploy:
    resources:
      limits:
        cpus: "0.25"
        memory: 128M
  depends_on:
    - bloomberg-grafana
    - bloomberg-watchlist-api
```

## Volumes

```yaml
volumes:
  grafana-data:
    name: bloomberg-grafana-data
  influxdb-data:
    name: bloomberg-influxdb-data
  influxdb-config:
    name: bloomberg-influxdb-config
  postgres-data:
    name: bloomberg-postgres-data
  prometheus-data:
    name: bloomberg-prometheus-data
  certbot-data:
    name: bloomberg-certbot-data
```

## Réseau

```yaml
networks:
  bloomberg-net:
    name: bloomberg-net
    driver: bridge
```

## Commandes Docker utiles

```bash
# Démarrage complet
docker compose up -d

# Arrêt (données conservées)
docker compose down

# Arrêt + suppression des données (⚠️ DESTRUCTIF)
docker compose down -v

# Rebuild un service après modif du code
docker compose build bloomberg-market-feeder
docker compose up -d bloomberg-market-feeder

# Voir les ressources utilisées
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Shell dans un container
docker exec -it bloomberg-grafana bash
docker exec -it bloomberg-influxdb bash
docker exec -it bloomberg-postgres psql -U $POSTGRES_USER -d bloomberg_config

# Nettoyer les images inutilisées
docker system prune -f
```

## Dockerfile type pour les collectors

```dockerfile
# collectors/market-feeder/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code applicatif
COPY . .

# Health check endpoint
EXPOSE 8080

# Lancement
CMD ["python", "-u", "main.py"]
```
