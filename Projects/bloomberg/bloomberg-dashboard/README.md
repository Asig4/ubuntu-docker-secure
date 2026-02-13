# Bloomberg-Style Grafana Dashboard

> Dashboard multi-usage style terminal Bloomberg TV, fully customisable.
> Marchés financiers • Crypto • Infra monitoring • News feed • Alerting

## Aperçu

Ce projet déploie un écosystème complet de monitoring temps réel inspiré de l'interface Bloomberg Terminal :

- **Ticker défilant** avec prix et variations en temps réel
- **Grille multi-panels** dense style salle de marché
- **News feed** avec analyse de sentiment
- **Alertes multi-canal** (Telegram, email, webhook)
- **Watchlists dynamiques** personnalisables par utilisateur
- **Thèmes Bloomberg** (Dark, Light, Trading Neon)

## Prérequis

| Composant | Version minimum | Rôle |
|-----------|----------------|------|
| VPS / Serveur | 4 vCPU, 8 GB RAM, 80 GB SSD | Hébergement |
| Ubuntu | 22.04 LTS | Système d'exploitation |
| Docker Engine | 24+ | Containerisation |
| Docker Compose | v2 | Orchestration |
| Nom de domaine | — | Accès HTTPS (optionnel) |

## Démarrage rapide

```bash
# 1. Cloner le repo
git clone https://github.com/votre-user/bloomberg-dashboard.git
cd bloomberg-dashboard

# 2. Copier et configurer l'environnement
cp config/.env.example .env
nano .env  # Remplir les API keys et mots de passe

# 3. Lancer l'infrastructure
docker compose up -d

# 4. Vérifier que tout tourne
docker compose ps

# 5. Accéder à Grafana
# → http://localhost:3000 (ou https://votre-domaine.com)
# Login par défaut : admin / (voir .env)
```

## Architecture

```
Internet → Nginx (SSL) → Grafana ← InfluxDB ← Market Feeder ← Binance/Yahoo/etc.
                           ↑         ↑
                           │     PostgreSQL ← Watchlist Manager (FastAPI)
                           │
                           ← Prometheus ← Node Exporter + cAdvisor
```

Voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) pour les détails complets.

## Structure du projet

```
bloomberg-dashboard/
├── CLAUDE.md                 # Instructions pour l'IA
├── README.md                 # Ce fichier
├── docker-compose.yml        # Orchestration Docker
├── .env.example              # Template variables d'environnement
│
├── docs/                     # Documentation complète
│   ├── ARCHITECTURE.md       # Architecture technique
│   ├── SETUP.md              # Installation pas à pas
│   ├── DOCKER.md             # Configuration Docker
│   ├── COLLECTORS.md         # Feeders de données
│   ├── DASHBOARDS.md         # Spécifications panels
│   ├── ALERTING.md           # Alertes & notifications
│   ├── API.md                # API Watchlist Manager
│   ├── SECURITY.md           # Checklist sécurité
│   ├── RUNBOOK.md            # Procédures opérationnelles
│   └── TROUBLESHOOTING.md    # Résolution de problèmes
│
├── config/                   # Templates de configuration
│   ├── .env.example
│   ├── grafana.ini
│   └── prometheus.yml
│
├── collectors/               # Scripts de collecte Python
│   ├── market-feeder/        # Prix, volumes, market data
│   ├── news-feeder/          # Actualités & sentiment
│   └── watchlist-manager/    # API CRUD watchlists
│
├── grafana/                  # Configuration Grafana
│   ├── provisioning/         # Auto-provisioning
│   │   ├── datasources/      # InfluxDB, PostgreSQL, Prometheus
│   │   ├── dashboards/       # Providers de dashboards
│   │   └── alerting/         # Rules & contact points
│   └── dashboards-json/      # Dashboards exportés
│
├── prometheus/               # Config Prometheus
├── nginx/                    # Reverse proxy + SSL
└── scripts/                  # Utilitaires (backup, setup, etc.)
```

## Documentation

| Document | Contenu |
|----------|---------|
| [SETUP.md](docs/SETUP.md) | Installation complète pas à pas |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Schéma technique détaillé |
| [DOCKER.md](docs/DOCKER.md) | Configuration de chaque container |
| [COLLECTORS.md](docs/COLLECTORS.md) | Comment fonctionnent les feeders |
| [DASHBOARDS.md](docs/DASHBOARDS.md) | Design de chaque panel Bloomberg |
| [ALERTING.md](docs/ALERTING.md) | Configurer les alertes multi-canal |
| [API.md](docs/API.md) | Endpoints de l'API Watchlist Manager |
| [SECURITY.md](docs/SECURITY.md) | Hardening et bonnes pratiques |
| [RUNBOOK.md](docs/RUNBOOK.md) | Que faire quand ça plante |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Solutions aux problèmes courants |
| [ROADMAP.md](ROADMAP_Bloomberg_Dashboard.md) | Planning du projet avec checkboxes |

## Commandes utiles

```bash
# Tout démarrer / arrêter
docker compose up -d
docker compose down

# Logs en temps réel
docker compose logs -f bloomberg-grafana
docker compose logs -f bloomberg-market-feeder

# Redémarrer un service
docker compose restart bloomberg-market-feeder

# Backup complet
./scripts/backup.sh

# Vérifier la santé de tous les services
./scripts/healthcheck.sh

# Mettre à jour les images
docker compose pull && docker compose up -d
```

## Équipe & Contribution

Projet initié par Antoine — Sprint février 2026.

Voir [CLAUDE.md](CLAUDE.md) pour les conventions de code et les règles du projet.

---

*Propulsé par Grafana, InfluxDB, Prometheus, Docker & beaucoup de café ☕*
