# Guide d'Installation Pas à Pas

> De zéro à un dashboard Bloomberg fonctionnel. Chaque étape est vérifiable.

## Prérequis

- Un VPS accessible en SSH (4 vCPU, 8 GB RAM minimum)
- Un nom de domaine pointant vers le VPS (optionnel mais recommandé)
- Tes clés API (voir section "Clés API" ci-dessous)

## Étape 1 — Préparer le VPS

### 1.1 Se connecter et mettre à jour

```bash
ssh root@ton-ip-vps

# Mise à jour système
apt update && apt upgrade -y

# Installer les utilitaires de base
apt install -y curl wget git htop nano ufw fail2ban
```

### 1.2 Créer un utilisateur dédié

```bash
# Créer l'utilisateur
adduser bloomberg
usermod -aG sudo bloomberg

# Copier les clés SSH
mkdir -p /home/bloomberg/.ssh
cp ~/.ssh/authorized_keys /home/bloomberg/.ssh/
chown -R bloomberg:bloomberg /home/bloomberg/.ssh

# Se reconnecter en tant que bloomberg
su - bloomberg
```

### 1.3 Configurer le firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Vérifier
sudo ufw status
```

**✅ Vérification** : `sudo ufw status` montre les 3 ports ouverts.

### 1.4 Configurer fail2ban

```bash
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 1.5 Configurer le timezone

```bash
sudo timedatectl set-timezone Europe/Paris
timedatectl
```

**✅ Vérification** : `timedatectl` montre `Europe/Paris`.

---

## Étape 2 — Installer Docker

### 2.1 Docker Engine

```bash
# Ajouter la clé GPG Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Ajouter le repo Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Installer
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker bloomberg
newgrp docker
```

**✅ Vérification** : `docker run hello-world` affiche un message de succès.

### 2.2 Vérifier Docker Compose

```bash
docker compose version
# Doit afficher: Docker Compose version v2.x.x
```

**✅ Vérification** : version 2.x confirmée.

---

## Étape 3 — Cloner et configurer le projet

### 3.1 Cloner le repo

```bash
cd ~
git clone https://github.com/votre-user/bloomberg-dashboard.git
cd bloomberg-dashboard
```

Ou si tu pars de zéro avec les fichiers de ce kit :
```bash
mkdir -p ~/bloomberg-dashboard
cd ~/bloomberg-dashboard
# Copier tous les fichiers du kit ici
```

### 3.2 Configurer les variables d'environnement

```bash
cp config/.env.example .env
nano .env
```

**Variables à remplir obligatoirement** :

| Variable | Où la trouver | Obligatoire |
|----------|---------------|-------------|
| `GRAFANA_ADMIN_PASSWORD` | Invente un mot de passe fort | ✅ |
| `INFLUXDB_PASSWORD` | Invente un mot de passe fort | ✅ |
| `INFLUXDB_TOKEN` | Sera généré au premier lancement | ✅ |
| `POSTGRES_PASSWORD` | Invente un mot de passe fort | ✅ |
| `JWT_SECRET` | `openssl rand -hex 32` | ✅ |
| `DOMAIN` | Ton nom de domaine | ⚠️ recommandé |
| `BINANCE_API_KEY` | https://www.binance.com/en/my/settings/api-management | ⚠️ optionnel |
| `COINGECKO_API_KEY` | https://www.coingecko.com/en/api/pricing | ⚠️ optionnel |
| `NEWSAPI_KEY` | https://newsapi.org/register | ⚠️ optionnel |
| `CRYPTOPANIC_TOKEN` | https://cryptopanic.com/developers/api/ | ⚠️ optionnel |
| `TELEGRAM_BOT_TOKEN` | https://t.me/BotFather | ⚠️ optionnel |
| `TELEGRAM_CHAT_ID` | Via @userinfobot | ⚠️ optionnel |

**Générer les mots de passe et secrets** :
```bash
# Générer un mot de passe fort
openssl rand -base64 24

# Générer le JWT secret
openssl rand -hex 32

# Générer le token InfluxDB
openssl rand -hex 32
```

**✅ Vérification** : `cat .env | grep -v '^#' | grep -v '^$'` montre toutes les variables remplies.

---

## Étape 4 — Premier lancement

### 4.1 Lancer l'infrastructure de base

```bash
# D'abord les bases de données seules
docker compose up -d bloomberg-influxdb bloomberg-postgres bloomberg-prometheus

# Attendre 30 secondes que tout démarre
sleep 30

# Vérifier
docker compose ps
```

**✅ Vérification** : 3 containers `healthy`.

### 4.2 Créer les buckets InfluxDB supplémentaires

```bash
# Les buckets additionnels (markets est créé automatiquement)
docker exec bloomberg-influxdb influx bucket create \
  -n news -o bloomberg -r 2160h -t $INFLUXDB_TOKEN

docker exec bloomberg-influxdb influx bucket create \
  -n infra -o bloomberg -r 360h -t $INFLUXDB_TOKEN

docker exec bloomberg-influxdb influx bucket create \
  -n custom -o bloomberg -r 0 -t $INFLUXDB_TOKEN

docker exec bloomberg-influxdb influx bucket create \
  -n markets_5min -o bloomberg -r 720h -t $INFLUXDB_TOKEN

docker exec bloomberg-influxdb influx bucket create \
  -n markets_1h -o bloomberg -r 8760h -t $INFLUXDB_TOKEN
```

**✅ Vérification** : `docker exec bloomberg-influxdb influx bucket list -o bloomberg` montre 6 buckets.

### 4.3 Vérifier PostgreSQL

```bash
docker exec -it bloomberg-postgres psql -U bloomberg_user -d bloomberg_config -c "\dt"
```

**✅ Vérification** : les tables `watchlists`, `user_layouts`, `alert_rules` existent.

### 4.4 Lancer tout le reste

```bash
docker compose up -d

# Vérifier que tout tourne
docker compose ps
```

**✅ Vérification** : tous les containers sont `Up` ou `healthy`.

### 4.5 Accéder à Grafana

```bash
# En local (si pas de domaine)
echo "Grafana disponible sur http://$(curl -s ifconfig.me):3000"

# Avec Nginx (production)
echo "Grafana disponible sur https://$DOMAIN"
```

Login : `admin` / le mot de passe dans `.env`

**✅ Vérification** : tu vois la page d'accueil Grafana.

---

## Étape 5 — Vérifier les datasources Grafana

Aller dans **Grafana → Configuration → Data Sources** :

### 5.1 InfluxDB
- URL : `http://bloomberg-influxdb:8086`
- Organisation : `bloomberg`
- Token : copier depuis `.env`
- Default bucket : `markets`
- Query language : **Flux**

### 5.2 PostgreSQL
- Host : `bloomberg-postgres:5432`
- Database : `bloomberg_config`
- User/Password : depuis `.env`
- SSL Mode : `disable` (réseau interne)

### 5.3 Prometheus
- URL : `http://bloomberg-prometheus:9090`
- Pas d'auth nécessaire (réseau interne)

**✅ Vérification** : le bouton "Save & Test" est vert pour les 3 datasources.

Si tu utilises le provisioning (recommandé), les datasources sont configurées automatiquement via `grafana/provisioning/datasources/`.

---

## Étape 6 — Premier test de données

### 6.1 Écrire un point test dans InfluxDB

```bash
docker exec bloomberg-influxdb influx write \
  -b markets -o bloomberg -t $INFLUXDB_TOKEN \
  "market_data,exchange=test,symbol=BTC/USDT,asset_type=crypto price=67234.50,volume_24h=28500000000 $(date +%s)000000000"
```

### 6.2 Vérifier dans Grafana

1. Aller dans **Explore**
2. Sélectionner la datasource **InfluxDB**
3. Requête Flux :
```flux
from(bucket: "markets")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "market_data")
```

**✅ Vérification** : tu vois le point de donnée BTC à 67234.50.

---

## Étape 7 — Configurer SSL (Optionnel mais recommandé)

### 7.1 Installer Certbot

```bash
sudo apt install -y certbot
```

### 7.2 Obtenir le certificat

```bash
# Arrêter Nginx temporairement
docker compose stop bloomberg-nginx

# Obtenir le certificat
sudo certbot certonly --standalone -d $DOMAIN --email ton@email.com --agree-tos --no-eff-email

# Copier les certificats
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ./nginx/ssl/
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ./nginx/ssl/
sudo chown bloomberg:bloomberg ./nginx/ssl/*

# Relancer Nginx
docker compose up -d bloomberg-nginx
```

### 7.3 Renouvellement automatique

```bash
# Ajouter un cron
(crontab -l 2>/dev/null; echo "0 3 1 * * certbot renew --quiet && docker compose restart bloomberg-nginx") | crontab -
```

**✅ Vérification** : `https://ton-domaine.com` affiche Grafana avec le cadenas vert.

---

## Récapitulatif des vérifications

| # | Étape | Commande de vérification | Résultat attendu |
|---|-------|-------------------------|------------------|
| 1 | Firewall | `sudo ufw status` | 3 ports ouverts |
| 2 | Docker | `docker run hello-world` | Message de succès |
| 3 | Compose | `docker compose version` | v2.x.x |
| 4 | .env | `cat .env \| wc -l` | 15+ lignes |
| 5 | Containers | `docker compose ps` | Tous `healthy` |
| 6 | InfluxDB buckets | `influx bucket list` | 6 buckets |
| 7 | PostgreSQL tables | `\dt` dans psql | 3 tables |
| 8 | Grafana UI | Navigateur | Page d'accueil visible |
| 9 | Datasources | Save & Test | 3x vert |
| 10 | Données test | Grafana Explore | Point BTC visible |
| 11 | SSL | https://domaine | Cadenas vert |

---

## En cas de problème

Voir [TROUBLESHOOTING.md](TROUBLESHOOTING.md) pour les solutions aux problèmes courants.

**Commande diagnostic rapide** :
```bash
# État de tous les services
docker compose ps

# Logs des 50 dernières lignes d'un service
docker compose logs --tail 50 bloomberg-grafana

# Espace disque
df -h

# RAM et CPU
htop
```
