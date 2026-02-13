# Checklist Sécurité

> Hardening du VPS, des services Docker, et des accès.

## Checklist de déploiement

### Niveau 1 — Obligatoire avant mise en prod

- [ ] **SSH** : connexion par clé uniquement, désactiver le login root et le mot de passe
  ```bash
  # /etc/ssh/sshd_config
  PermitRootLogin no
  PasswordAuthentication no
  PubkeyAuthentication yes
  ```
- [ ] **Firewall UFW** : seuls les ports 22, 80, 443 ouverts
- [ ] **fail2ban** : activé et configuré pour SSH
- [ ] **Mots de passe** : tous générés avec `openssl rand -base64 24` (min 24 chars)
- [ ] **Fichier .env** : jamais commité dans git (ajouté à `.gitignore`)
- [ ] **Ports Docker** : seul Nginx expose des ports (80, 443)
- [ ] **SSL/TLS** : certificat Let's Encrypt valide, renouvellement auto
- [ ] **Grafana admin** : mot de passe changé depuis le défaut

### Niveau 2 — Recommandé

- [ ] **Docker** : limites CPU/RAM sur chaque container
- [ ] **Nginx** : rate limiting (10 req/s), headers de sécurité
- [ ] **API Keys** : permissions minimales (lecture seule quand possible)
- [ ] **Grafana roles** : Viewer par défaut, Editor sur demande, Admin restreint
- [ ] **PostgreSQL** : user applicatif avec permissions limitées (pas superuser)
- [ ] **InfluxDB** : tokens avec permissions par bucket (pas le token admin partout)
- [ ] **Backups** : quotidiens, testés, stockés hors VPS
- [ ] **Mises à jour** : apt + images Docker à jour

### Niveau 3 — Avancé

- [ ] **2FA** sur Grafana (via OAuth Google/GitHub)
- [ ] **VPN** (Tailscale/WireGuard) pour l'accès admin
- [ ] **Audit log** : activer les logs d'accès Nginx
- [ ] **Monitoring sécurité** : alertes sur login SSH, sudo, container restarts
- [ ] **Scan de vulnérabilités** : `docker scout` ou `trivy` sur les images

---

## Nginx — Headers de sécurité

```nginx
# À ajouter dans la config Nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' wss:;" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

# Rate limiting
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
```

## Gestion des secrets

### Ce qui va dans `.env` (jamais en clair dans le code)

```
# Mots de passe
GRAFANA_ADMIN_PASSWORD=
INFLUXDB_PASSWORD=
POSTGRES_PASSWORD=

# Tokens
INFLUXDB_TOKEN=
JWT_SECRET=

# API Keys externes
BINANCE_API_KEY=
BINANCE_SECRET=
COINGECKO_API_KEY=
NEWSAPI_KEY=
CRYPTOPANIC_TOKEN=

# Notifications
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
SMTP_PASSWORD=
```

### Bonnes pratiques

1. **Ne jamais commiter `.env`** — le fichier `.gitignore` doit contenir `.env`
2. **Utiliser `.env.example`** — template sans valeurs sensibles
3. **Rotation des tokens** — changer les tokens tous les 90 jours
4. **Permissions minimales** — chaque API key ne doit avoir que les droits nécessaires
5. **Pas de secrets dans les logs** — vérifier que les collectors ne loguent pas les tokens

## InfluxDB — Tokens avec permissions limitées

Au lieu d'utiliser le token admin partout, créer des tokens spécifiques :

```bash
# Token lecture seule pour Grafana
docker exec bloomberg-influxdb influx auth create \
  --org bloomberg \
  --read-bucket markets \
  --read-bucket news \
  --read-bucket infra \
  --description "Grafana read-only"

# Token écriture pour le Market Feeder
docker exec bloomberg-influxdb influx auth create \
  --org bloomberg \
  --write-bucket markets \
  --description "Market Feeder write"

# Token écriture pour le News Feeder
docker exec bloomberg-influxdb influx auth create \
  --org bloomberg \
  --write-bucket news \
  --description "News Feeder write"
```

## PostgreSQL — User applicatif

```sql
-- Créer un user avec permissions limitées (pas superuser)
CREATE USER bloomberg_app WITH PASSWORD 'mot-de-passe-fort';
GRANT CONNECT ON DATABASE bloomberg_config TO bloomberg_app;
GRANT USAGE ON SCHEMA public TO bloomberg_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bloomberg_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bloomberg_app;

-- Le user dans .env pour les collectors doit être bloomberg_app, pas postgres
```

## Monitoring sécurité

### Alertes à configurer

| Événement | Détection | Notification |
|-----------|-----------|--------------|
| Login SSH échoué | fail2ban log | Telegram (critique) |
| Container redémarré | Prometheus | Telegram |
| Trafic anormal | Nginx rate limit atteint | Email |
| Disque > 90% | Prometheus | Telegram + Email |
| Certificat SSL expire dans 7j | Cron check | Email |
| Aucune donnée depuis 10 min | Dead man's switch | Telegram (critique) |
