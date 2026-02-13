# Runbook — Procédures Opérationnelles

> Que faire quand quelque chose tombe. Procédures pas-à-pas.

## Procédure 1 — Un container a crashé

**Symptôme** : le dashboard affiche "No data" sur certains panels, ou une alerte Telegram arrive.

```bash
# 1. Identifier le container en erreur
docker compose ps

# 2. Voir les logs du container
docker compose logs --tail 100 bloomberg-{service}

# 3. Redémarrer le container
docker compose restart bloomberg-{service}

# 4. Vérifier qu'il est reparti
docker compose ps
# Doit afficher "Up" et "healthy"

# 5. Si ça ne marche pas, rebuild
docker compose build bloomberg-{service}
docker compose up -d bloomberg-{service}
```

---

## Procédure 2 — InfluxDB saturé (disque plein)

**Symptôme** : erreurs d'écriture dans les logs du Market Feeder, panels "No data".

```bash
# 1. Vérifier l'espace disque
df -h
docker system df

# 2. Vérifier la taille d'InfluxDB
docker exec bloomberg-influxdb du -sh /var/lib/influxdb2/

# 3. Supprimer les données anciennes manuellement
docker exec bloomberg-influxdb influx delete \
  --org bloomberg \
  --bucket markets \
  --start 1970-01-01T00:00:00Z \
  --stop $(date -d "8 days ago" +%Y-%m-%dT%H:%M:%SZ) \
  -t $INFLUXDB_TOKEN

# 4. Nettoyer les images Docker inutilisées
docker system prune -f

# 5. Vérifier que l'espace est libéré
df -h
```

---

## Procédure 3 — Market Feeder ne collecte plus

**Symptôme** : alerte "Dead man's switch" reçue, pas de nouvelles données.

```bash
# 1. Vérifier le health check
docker exec bloomberg-market-feeder curl -s http://localhost:8080/health | python3 -m json.tool

# 2. Vérifier les logs
docker compose logs --tail 200 bloomberg-market-feeder

# Causes fréquentes:
# - Rate limit API Binance → attendre 1 minute
# - API key expirée → régénérer dans .env
# - InfluxDB down → vérifier InfluxDB d'abord
# - Erreur réseau → vérifier la connectivité

# 3. Redémarrer
docker compose restart bloomberg-market-feeder

# 4. Vérifier que les données reviennent
docker exec bloomberg-influxdb influx query \
  'from(bucket:"markets") |> range(start:-5m) |> count()' \
  --org bloomberg -t $INFLUXDB_TOKEN
```

---

## Procédure 4 — Grafana inaccessible

**Symptôme** : page blanche ou erreur 502/504 sur le navigateur.

```bash
# 1. Vérifier Nginx
docker compose logs --tail 50 bloomberg-nginx

# 2. Vérifier Grafana
docker compose logs --tail 50 bloomberg-grafana
docker compose ps bloomberg-grafana

# 3. Si Nginx est down
docker compose restart bloomberg-nginx

# 4. Si Grafana est down
docker compose restart bloomberg-grafana

# 5. Accès de secours (bypass Nginx)
# Temporairement exposer le port Grafana directement
# Dans docker-compose.yml, ajouter sous bloomberg-grafana:
#   ports:
#     - "3000:3000"
# Puis: docker compose up -d bloomberg-grafana
# Accès: http://ton-ip:3000
# ⚠️ RETIRER après dépannage
```

---

## Procédure 5 — Certificat SSL expiré

**Symptôme** : navigateur affiche "Connexion non sécurisée".

```bash
# 1. Vérifier l'expiration du certificat
sudo certbot certificates

# 2. Renouveler manuellement
sudo certbot renew

# 3. Copier les nouveaux certificats
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ./nginx/ssl/
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ./nginx/ssl/

# 4. Relancer Nginx
docker compose restart bloomberg-nginx

# 5. Vérifier
curl -I https://ton-domaine.com
# Doit afficher HTTP/2 200
```

---

## Procédure 6 — Backup & Restauration

### Backup manuel

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/home/bloomberg/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

echo "=== Backup PostgreSQL ==="
docker exec bloomberg-postgres pg_dump -U bloomberg_user bloomberg_config > $BACKUP_DIR/postgres.sql

echo "=== Backup InfluxDB ==="
docker exec bloomberg-influxdb influx backup /tmp/influx-backup --org bloomberg -t $INFLUXDB_TOKEN
docker cp bloomberg-influxdb:/tmp/influx-backup $BACKUP_DIR/influxdb/

echo "=== Backup Grafana dashboards ==="
cp -r grafana/dashboards-json/ $BACKUP_DIR/dashboards/

echo "=== Backup config ==="
cp .env $BACKUP_DIR/dot-env-backup
cp docker-compose.yml $BACKUP_DIR/

echo "=== Compression ==="
tar -czf $BACKUP_DIR.tar.gz -C $(dirname $BACKUP_DIR) $(basename $BACKUP_DIR)
rm -rf $BACKUP_DIR

echo "Backup terminé: $BACKUP_DIR.tar.gz"
echo "Taille: $(du -sh $BACKUP_DIR.tar.gz | cut -f1)"
```

### Restauration

```bash
# 1. Extraire le backup
tar -xzf backup_20260212.tar.gz
cd backup_20260212

# 2. Restaurer PostgreSQL
docker exec -i bloomberg-postgres psql -U bloomberg_user bloomberg_config < postgres.sql

# 3. Restaurer InfluxDB
docker cp influxdb/ bloomberg-influxdb:/tmp/influx-restore
docker exec bloomberg-influxdb influx restore /tmp/influx-restore --org bloomberg -t $INFLUXDB_TOKEN

# 4. Restaurer les dashboards
cp -r dashboards/* ../grafana/dashboards-json/
docker compose restart bloomberg-grafana
```

### Cron de backup automatique

```bash
# Backup quotidien à 3h du matin
(crontab -l 2>/dev/null; echo "0 3 * * * /home/bloomberg/bloomberg-dashboard/scripts/backup.sh >> /var/log/bloomberg-backup.log 2>&1") | crontab -

# Nettoyage des backups > 30 jours
(crontab -l 2>/dev/null; echo "0 4 * * 0 find /home/bloomberg/backups -name '*.tar.gz' -mtime +30 -delete") | crontab -
```

---

## Procédure 7 — Mise à jour des images Docker

```bash
# 1. Backup avant mise à jour
./scripts/backup.sh

# 2. Tirer les nouvelles images
docker compose pull

# 3. Redémarrer avec les nouvelles images
docker compose up -d

# 4. Vérifier que tout fonctionne
docker compose ps
# Tester le dashboard dans le navigateur

# 5. Nettoyer les anciennes images
docker image prune -f
```

---

## Procédure 8 — Ajout d'un nouveau membre à l'équipe

```bash
# 1. Créer le compte Grafana
# Grafana → Administration → Users → New user
# Role: Viewer (par défaut)

# 2. Créer un user API pour les watchlists
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "nouveau_membre", "password": "mot-de-passe-fort"}'

# 3. Configurer les notifications
# Le membre rejoint le groupe Telegram de l'équipe

# 4. Documenter dans le README
```

---

## Contacts d'urgence

| Quoi | Qui | Comment |
|------|-----|---------|
| VPS down | Hébergeur (Hetzner/OVH) | Panel admin + ticket support |
| API Binance | Binance | https://www.binance.com/en/support |
| Domaine/DNS | Registrar | Panel admin du registrar |
| Grafana bug | Communauté | https://community.grafana.com |
