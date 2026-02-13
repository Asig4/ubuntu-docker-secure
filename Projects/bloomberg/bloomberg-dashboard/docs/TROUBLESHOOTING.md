# Troubleshooting — Résolution de Problèmes

> Solutions aux problèmes les plus courants.

## Diagnostic rapide

```bash
# Commande universelle de diagnostic
echo "=== Docker ===" && docker compose ps && echo "" && \
echo "=== Disque ===" && df -h / && echo "" && \
echo "=== RAM ===" && free -h && echo "" && \
echo "=== CPU ===" && uptime && echo "" && \
echo "=== Grafana Health ===" && curl -s http://localhost:3000/api/health 2>/dev/null || echo "Grafana DOWN" && echo "" && \
echo "=== InfluxDB Health ===" && docker exec bloomberg-influxdb influx ping 2>/dev/null || echo "InfluxDB DOWN"
```

---

## Problèmes fréquents

### 1. "No data" dans les panels Grafana

**Causes possibles** :

| Cause | Diagnostic | Solution |
|-------|-----------|----------|
| Mauvaise datasource | Grafana → Settings → Data Sources | Vérifier URL et credentials |
| Mauvais bucket | Vérifier `from(bucket: "...")` | Corriger le nom du bucket |
| Mauvais range | Le range est trop court | Élargir : `range(start: -1h)` |
| Collector down | `docker compose ps` | Restart le collector |
| InfluxDB down | `docker exec bloomberg-influxdb influx ping` | Restart InfluxDB |
| Pas encore de données | Projet vient de démarrer | Attendre 1-2 min que les collectors envoient |

**Vérification dans Grafana Explore** :
```flux
// Vérifier qu'il y a des données
from(bucket: "markets")
  |> range(start: -1h)
  |> count()
```

### 2. Container en "Restarting" en boucle

```bash
# 1. Voir les logs pour identifier l'erreur
docker compose logs --tail 50 bloomberg-{service}

# 2. Causes fréquentes:
# - Variable .env manquante → vérifier .env
# - Port déjà utilisé → changer le port ou kill le process
# - Dépendance pas prête → la BDD met plus longtemps à démarrer
# - Image corrompue → rebuild

# 3. Solution universelle
docker compose down
docker compose build --no-cache bloomberg-{service}
docker compose up -d
```

### 3. Erreur de connexion InfluxDB depuis Grafana

**Message** : `datasource: InfluxDB - error: 401 Unauthorized`

```bash
# 1. Vérifier que le token est correct
docker exec bloomberg-influxdb influx auth list --org bloomberg

# 2. Vérifier la connectivité interne
docker exec bloomberg-grafana curl -s http://bloomberg-influxdb:8086/health

# 3. Reconfigurer la datasource
# Grafana → Data Sources → InfluxDB → Edit
# - URL: http://bloomberg-influxdb:8086
# - Organization: bloomberg
# - Token: (copier depuis .env)
# - Default bucket: markets
```

### 4. Erreur de connexion PostgreSQL

**Message** : `FATAL: password authentication failed`

```bash
# 1. Vérifier les credentials
docker exec bloomberg-postgres psql -U bloomberg_user -d bloomberg_config -c "SELECT 1"

# 2. Si le mot de passe a changé, reset
docker exec bloomberg-postgres psql -U postgres -c \
  "ALTER USER bloomberg_user PASSWORD 'nouveau-mot-de-passe';"

# 3. Mettre à jour .env et redémarrer les services concernés
docker compose restart bloomberg-watchlist-api bloomberg-market-feeder bloomberg-grafana
```

### 5. WebSocket Binance déconnecté

**Log** : `WebSocket connection closed` ou `ConnectionResetError`

Causes et solutions :

| Cause | Solution |
|-------|----------|
| Binance maintenance | Attendre, le reconnect auto gère |
| IP bloquée | Vérifier si le VPS est dans un pays bloqué par Binance |
| Trop de connexions | Réduire le nombre de streams simultanés (max 200) |
| Firewall bloque WSS | Vérifier que le port 9443 sortant est ouvert |

Le reconnect automatique avec backoff exponentiel devrait résoudre les déconnexions temporaires.

### 6. Rate limit atteint sur une API

**Log** : `429 Too Many Requests`

```
# Ajuster les intervalles dans .env

# CoinGecko (gratuit: 30 req/min)
COINGECKO_INTERVAL=120  # 1 req toutes les 2 minutes

# NewsAPI (gratuit: 100 req/jour)
NEWSAPI_INTERVAL=900  # 1 req toutes les 15 minutes

# Binance REST (1200 req/min)
BINANCE_REST_INTERVAL=5  # Rarement un problème
```

### 7. Ticker défilant ne s'affiche pas

```
# Vérifier dans grafana.ini que le HTML non-sanitisé est autorisé
[panels]
disable_sanitize_html = true

# Redémarrer Grafana après modification
docker compose restart bloomberg-grafana

# Vérifier que le plugin dynamictext est installé
docker exec bloomberg-grafana grafana cli plugins ls
# Doit montrer: marcusolsson-dynamictext-panel
```

### 8. Certificat SSL ne se renouvelle pas

```bash
# 1. Tester le renouvellement
sudo certbot renew --dry-run

# 2. Si erreur "port 80 in use"
docker compose stop bloomberg-nginx
sudo certbot renew
docker compose start bloomberg-nginx

# 3. Vérifier le cron
crontab -l | grep certbot
```

### 9. Docker prend trop de place disque

```bash
# 1. Voir l'utilisation
docker system df

# 2. Nettoyer les images non utilisées
docker image prune -a -f

# 3. Nettoyer les volumes orphelins
docker volume prune -f

# 4. Nettoyer les build cache
docker builder prune -f

# 5. Nuclear option (⚠️ supprime tout sauf les containers/volumes actifs)
docker system prune -a -f
```

### 10. Grafana très lent

```
# 1. Vérifier les requêtes lentes
# Grafana → Server Admin → Query History

# 2. Causes fréquentes:
# - Requête Flux qui scan trop de données → réduire le range
# - Trop de panels → simplifier le dashboard
# - InfluxDB sous-dimensionné → augmenter la RAM

# 3. Optimiser une requête Flux lente
# AVANT (lent):
from(bucket: "markets") |> range(start: -30d) |> filter(...)

# APRÈS (rapide):
from(bucket: "markets_5min") |> range(start: -30d) |> filter(...)
# Utiliser le bucket downsamplé pour les grands ranges

# 4. Activer le cache Grafana
# grafana.ini:
# [caching]
# enabled = true
```

---

## Commandes de debug utiles

```bash
# Shell interactif dans un container
docker exec -it bloomberg-grafana bash
docker exec -it bloomberg-influxdb bash
docker exec -it bloomberg-postgres psql -U bloomberg_user -d bloomberg_config

# Voir la config réseau Docker
docker network inspect bloomberg-net

# Tester la connectivité entre containers
docker exec bloomberg-grafana ping bloomberg-influxdb

# Voir les ressources par container
docker stats --no-stream

# Voir les logs de TOUS les services
docker compose logs --tail 20

# Vérifier les ports ouverts sur le VPS
sudo ss -tlnp
```
