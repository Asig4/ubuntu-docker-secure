# Alerting & Notifications

> Configuration complète du système d'alertes multi-canal.

## Architecture d'alerting

```
┌──────────────────────┐
│  Grafana Alerting     │
│  (Unified Alerting)   │
│                       │
│  Rules:               │
│  • Prix > seuil       │
│  • Variation % > X    │
│  • Volume spike       │
│  • Infra anomalie     │
│  • Collector down     │
│  • Dead man's switch  │
└──────────┬────────────┘
           │
           ▼
┌──────────────────────┐
│  Contact Points       │
│                       │
│  • Telegram Bot  ─────┼──► Channel Telegram équipe
│  • Email SMTP    ─────┼──► Boîtes mail individuelles
│  • Webhook       ─────┼──► Discord / Slack / Custom
└──────────────────────┘
```

## Contact Points

### 1. Telegram Bot

**Création du bot** :
1. Ouvrir @BotFather sur Telegram
2. `/newbot` → nommer le bot (ex: `BloombergAlertBot`)
3. Copier le token → `TELEGRAM_BOT_TOKEN` dans `.env`
4. Créer un groupe Telegram pour l'équipe
5. Ajouter le bot au groupe
6. Obtenir le chat ID via `https://api.telegram.org/bot<TOKEN>/getUpdates`
7. Copier le chat_id → `TELEGRAM_CHAT_ID` dans `.env`

**Configuration Grafana** :
```
Grafana → Alerting → Contact Points → New Contact Point
  Name: Telegram - Équipe
  Type: Telegram
  Bot Token: ${TELEGRAM_BOT_TOKEN}
  Chat ID: ${TELEGRAM_CHAT_ID}
  Parse Mode: HTML
```

**Template de message** :
```
🚨 <b>ALERTE: {{ .Labels.alertname }}</b>

Asset: <b>{{ .Labels.symbol }}</b>
Exchange: {{ .Labels.exchange }}
Condition: {{ .Annotations.description }}
Valeur: <b>{{ .Values.A }}</b>
Seuil: {{ .Annotations.threshold }}

⏰ {{ .StartsAt.Format "15:04:05 MST" }}
🔗 <a href="{{ .GeneratorURL }}">Voir dans Grafana</a>
```

### 2. Email SMTP

**Configuration avec Brevo (ex-Sendinblue)** — service gratuit jusqu'à 300 emails/jour :

1. Créer un compte sur https://www.brevo.com
2. Aller dans Settings → SMTP & API
3. Récupérer les credentials SMTP

**Variables .env** :
```
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=ton-email@example.com
SMTP_PASSWORD=ton-smtp-key
SMTP_FROM=alerts@ton-domaine.com
```

**Configuration grafana.ini** :
```ini
[smtp]
enabled = true
host = smtp-relay.brevo.com:587
user = ${SMTP_USER}
password = ${SMTP_PASSWORD}
from_address = alerts@ton-domaine.com
from_name = Bloomberg Dashboard
startTLS_policy = MandatoryStartTLS
```

**Configuration Grafana Contact Point** :
```
Name: Email - Équipe
Type: Email
Addresses: antoine@example.com; collegue@example.com
Subject: [BLOOMBERG] {{ .Labels.alertname }} - {{ .Labels.symbol }}
```

### 3. Webhook (Discord / Slack / Custom)

**Discord** :
1. Serveur Discord → Paramètres du channel → Intégrations → Webhooks
2. Créer un webhook, copier l'URL

**Configuration Grafana** :
```
Name: Discord - Alertes
Type: Webhook
URL: https://discord.com/api/webhooks/xxx/yyy
HTTP Method: POST
```

---

## Alert Rules

### Catégorie 1 — Alertes de prix

#### Prix au-dessus d'un seuil

```yaml
name: "Prix au-dessus du seuil"
folder: Bloomberg Alerts
group: Market Alerts
condition: A
for: 0s  # Immédiat

datasource: InfluxDB
query_A: |
  from(bucket: "markets")
    |> range(start: -5m)
    |> filter(fn: (r) => r._measurement == "market_data")
    |> filter(fn: (r) => r.symbol == "BTC/USDT")
    |> filter(fn: (r) => r._field == "price")
    |> last()

condition: "WHEN last() OF query(A) IS ABOVE 70000"

annotations:
  summary: "BTC/USDT au-dessus de $70,000"
  description: "Le prix de BTC a franchi le seuil de $70,000"
  threshold: "70000"

labels:
  severity: "high"
  category: "market"
  symbol: "BTC/USDT"
```

#### Variation % importante

```yaml
name: "Variation 1h supérieure à 5%"
condition: |
  WHEN last() OF query(A) IS ABOVE 5
  OR WHEN last() OF query(A) IS BELOW -5

query_A: |
  from(bucket: "markets")
    |> range(start: -5m)
    |> filter(fn: (r) => r._measurement == "market_data")
    |> filter(fn: (r) => r._field == "change_pct_1h")
    |> last()

annotations:
  summary: "{{ $labels.symbol }} a bougé de plus de 5% en 1h"
```

#### Volume spike

```yaml
name: "Spike de volume"
condition: |
  WHEN last() OF query(A) IS ABOVE avg() OF query(B) * 3

query_A: |
  # Volume actuel
  from(bucket: "markets") |> range(start: -5m) |> filter(fn: (r) => r._field == "volume_24h") |> last()

query_B: |
  # Volume moyen sur 7 jours
  from(bucket: "markets") |> range(start: -7d) |> filter(fn: (r) => r._field == "volume_24h") |> mean()

annotations:
  summary: "Volume de {{ $labels.symbol }} x3 au-dessus de la moyenne 7j"
```

### Catégorie 2 — Alertes infrastructure

#### CPU élevé

```yaml
name: "CPU > 80%"
datasource: Prometheus
query: 100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
condition: "IS ABOVE 80"
for: 5m  # Pendant 5 minutes consécutives

annotations:
  summary: "CPU du VPS au-dessus de 80% depuis 5 minutes"
labels:
  severity: "warning"
  category: "infra"
```

#### RAM élevée

```yaml
name: "RAM > 85%"
query: (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100
condition: "IS ABOVE 85"
for: 5m
```

#### Disque plein

```yaml
name: "Disque > 90%"
query: (1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100
condition: "IS ABOVE 90"
for: 0s  # Immédiat

labels:
  severity: "critical"
```

#### Container crash

```yaml
name: "Container redémarré"
query: increase(container_restart_count{name=~"bloomberg.*"}[5m])
condition: "IS ABOVE 0"
for: 0s
```

### Catégorie 3 — Dead Man's Switch

Alerte qui se déclenche si le Market Feeder **arrête** d'envoyer des données.

```yaml
name: "Market Feeder silencieux"
query: |
  from(bucket: "markets")
    |> range(start: -5m)
    |> filter(fn: (r) => r._measurement == "market_data")
    |> count()

condition: "IS BELOW 1"  # 0 points en 5 minutes = feeder mort
for: 5m

annotations:
  summary: "Le Market Feeder n'a envoyé aucune donnée depuis 5 minutes"
labels:
  severity: "critical"
  category: "system"
```

---

## Notification Policies

```yaml
# Politique par défaut
default_policy:
  receiver: "Telegram - Équipe"
  group_by: ["alertname", "symbol"]
  group_wait: 30s       # Attendre 30s avant d'envoyer (regroupe les alertes)
  group_interval: 5m    # Minimum 5m entre deux groupes
  repeat_interval: 4h   # Re-notification toutes les 4h si toujours firing

# Politique pour les alertes critiques
routes:
  - matchers:
      - severity = critical
    receiver: "Telegram - Équipe"
    group_wait: 0s       # Envoi immédiat
    repeat_interval: 30m # Re-notification toutes les 30m

  - matchers:
      - category = infra
    receiver: "Email - Équipe"
    group_wait: 1m
    repeat_interval: 1h

# Silences (mute pendant maintenance)
# Configurable via Grafana UI : Alerting → Silences
```

## Horaires de silence

Pour éviter les notifications pendant la nuit (sauf critiques) :

```yaml
mute_timings:
  - name: "Night silence"
    time_intervals:
      - times:
          - start_time: "23:00"
            end_time: "07:00"
        weekdays: ["monday:friday"]
        location: "Europe/Paris"
```

Appliquer ce mute timing aux routes non-critiques uniquement.

## Tester les alertes

```bash
# 1. Écrire une donnée de test qui déclenche une alerte
docker exec bloomberg-influxdb influx write \
  -b markets -o bloomberg -t $INFLUXDB_TOKEN \
  "market_data,exchange=test,symbol=BTC/USDT,asset_type=crypto price=999999.00 $(date +%s)000000000"

# 2. Vérifier dans Grafana → Alerting → Alert Rules
# Le statut devrait passer à "Firing"

# 3. Vérifier que la notification Telegram est reçue

# 4. Nettoyer la donnée de test
# (elle sera supprimée automatiquement par la retention policy)
```
