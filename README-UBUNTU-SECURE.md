# Ubuntu Docker Sécurisé - Guide Complet

## Vue d'ensemble

Conteneur Ubuntu 24.04 optimisé avec **sécurité maximale** pour héberger des services et applications multi-langages.

### Caractéristiques principales

✅ **Sécurité maximale**
- Utilisateur non-root (UID 1000)
- Capabilities Linux minimales
- Système de fichiers durci
- Réseau isolé avec accès internet contrôlé

✅ **Volume persistant de 60GB**
- Données persistantes sur `/data`
- Isolé du système de fichiers du conteneur
- Permissions strictes (700)

✅ **Optimisations**
- Image minimale (~30MB base)
- Multi-stage build
- Layers optimisés
- Health checks intégrés

✅ **Isolation réseau**
- Réseau privé dédié (172.20.0.0/16)
- Accès internet via NAT
- Isolation des autres conteneurs
- DNS sécurisés (Cloudflare + Google)

---

## Installation Rapide

### Prérequis

- Docker 20.10+
- Docker Compose 1.29+
- Au moins 60GB d'espace disque disponible

### Déploiement en 3 étapes

```bash
# 1. Rendre le script exécutable
chmod +x deploy-secure-ubuntu.sh

# 2. Démarrer le conteneur
./deploy-secure-ubuntu.sh start

# 3. Vérifier le statut
./deploy-secure-ubuntu.sh status
```

---

## Structure des Fichiers

```
.
├── Dockerfile                    # Image Ubuntu sécurisée
├── docker-compose.yml            # Configuration complète
├── deploy-secure-ubuntu.sh       # Script de gestion
├── README-UBUNTU-SECURE.md       # Cette documentation
└── data/                         # Volume 60GB (créé automatiquement)
```

---

## Utilisation

### Commandes de base

```bash
# Démarrer le conteneur
./deploy-secure-ubuntu.sh start

# Arrêter le conteneur
./deploy-secure-ubuntu.sh stop

# Redémarrer le conteneur
./deploy-secure-ubuntu.sh restart

# Voir les logs en temps réel
./deploy-secure-ubuntu.sh logs

# Afficher le statut détaillé
./deploy-secure-ubuntu.sh status

# Ouvrir un shell dans le conteneur
./deploy-secure-ubuntu.sh exec
```

### Accéder au conteneur

```bash
# Via le script
./deploy-secure-ubuntu.sh exec

# Ou directement avec docker
docker exec -it ubuntu-secure-app /bin/bash
```

### Gérer les données

Le volume persistant est monté sur `/data` dans le conteneur :

```bash
# Depuis l'hôte
ls -la ./data/

# Depuis le conteneur
docker exec ubuntu-secure-app ls -la /data/
```

---

## Configuration Avancée

### Exposer des ports

Éditez `docker-compose.yml` et décommentez la section `ports` :

```yaml
ports:
  - "8080:8080"  # Format: "port_hote:port_conteneur"
```

### Ajouter des variables d'environnement

Dans `docker-compose.yml`, section `environment` :

```yaml
environment:
  - TZ=Europe/Paris
  - NODE_ENV=production
  - DATABASE_URL=your_database_url
```

### Modifier les ressources CPU/RAM

Dans `docker-compose.yml`, section `deploy` :

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'      # Maximum 4 CPU cores
      memory: 8G       # Maximum 8GB RAM
```

### Activer le système de fichiers en lecture seule

Dans `docker-compose.yml`, décommentez :

```yaml
read_only: true
```

⚠️ **Attention :** Votre application doit supporter cette configuration.

### Ajouter des capabilities Linux

Si votre application nécessite des capabilities spécifiques, éditez `docker-compose.yml` :

```yaml
cap_add:
  - NET_BIND_SERVICE  # Pour ports < 1024
  - CHOWN            # Pour changer propriétaire fichiers
  - DAC_OVERRIDE     # Pour bypass permissions
```

⚠️ **Sécurité :** Ajoutez uniquement les capabilities strictement nécessaires.

---

## Personnalisation de l'Image

### Installer des packages supplémentaires

Éditez le `Dockerfile`, section `Stage 1: Base` :

```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        tzdata \
        curl \           # Ajoutez vos packages ici
        wget \
        git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

### Exemple : Image avec Node.js

```dockerfile
# Après la section base, ajoutez :
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

### Exemple : Image avec Python

```dockerfile
# Après la section base, ajoutez :
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

Après modification, rebuild l'image :

```bash
./deploy-secure-ubuntu.sh restart
```

---

## Sécurité

### Analyse des vulnérabilités

```bash
# Scanner l'image avec Trivy
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy:latest image ubuntu-secure-app
```

### Vérifier les permissions

```bash
# Vérifier l'utilisateur du conteneur
docker exec ubuntu-secure-app whoami
# Devrait retourner: appuser

# Vérifier les permissions du volume
docker exec ubuntu-secure-app ls -ld /data
# Devrait retourner: drwx------ 2 appuser appuser
```

### Vérifier l'isolation réseau

```bash
# Lister les réseaux
docker network ls | grep secure_network

# Inspecter le réseau
docker network inspect secure_network
```

### Mises à jour de sécurité

```bash
# Rebuild l'image pour obtenir les dernières mises à jour
docker-compose build --no-cache

# Redémarrer avec la nouvelle image
./deploy-secure-ubuntu.sh restart
```

---

## Monitoring

### Vérifier l'état de santé

```bash
# Via le script
./deploy-secure-ubuntu.sh status

# Via docker
docker inspect --format='{{.State.Health.Status}}' ubuntu-secure-app
```

### Surveiller l'utilisation des ressources

```bash
# Utilisation en temps réel
docker stats ubuntu-secure-app

# Utilisation du volume
docker exec ubuntu-secure-app du -sh /data
```

### Logs

```bash
# Logs en temps réel
./deploy-secure-ubuntu.sh logs

# Dernières 100 lignes
docker logs --tail 100 ubuntu-secure-app

# Logs depuis une date
docker logs --since 2024-01-01T00:00:00 ubuntu-secure-app
```

---

## Maintenance

### Sauvegarde du volume

```bash
# Créer une archive du volume
tar -czf backup-$(date +%Y%m%d).tar.gz ./data/

# Ou avec docker
docker run --rm \
  -v $(pwd)/data:/data \
  -v $(pwd):/backup \
  ubuntu tar -czf /backup/backup-$(date +%Y%m%d).tar.gz /data
```

### Restauration du volume

```bash
# Restaurer depuis une archive
tar -xzf backup-20240201.tar.gz -C ./
```

### Nettoyage

```bash
# Arrêter et supprimer le conteneur
./deploy-secure-ubuntu.sh stop

# Supprimer l'image
docker rmi ubuntu-secure-app

# Supprimer le réseau
docker network rm secure_network

# Nettoyer les volumes inutilisés
docker volume prune
```

---

## Dépannage

### Le conteneur ne démarre pas

```bash
# Vérifier les logs d'erreur
docker logs ubuntu-secure-app

# Vérifier la configuration
docker-compose config
```

### Problème de permissions sur /data

```bash
# Vérifier le propriétaire
ls -la ./data/

# Corriger les permissions (nécessite sudo)
sudo chown -R 1000:1000 ./data/
sudo chmod 700 ./data/
```

### Le health check échoue

```bash
# Vérifier manuellement
docker exec ubuntu-secure-app test -d /data && echo "OK" || echo "FAIL"

# Inspecter les détails
docker inspect ubuntu-secure-app | grep -A 10 Health
```

### Pas d'accès internet dans le conteneur

```bash
# Tester la connectivité
docker exec ubuntu-secure-app ping -c 3 1.1.1.1

# Vérifier la configuration réseau
docker network inspect secure_network
```

---

## Feuille de route

### Améliorations futures possibles

- [ ] Profile Seccomp personnalisé
- [ ] Intégration avec AppArmor
- [ ] Surveillance avec Prometheus
- [ ] Rotation automatique des logs
- [ ] Backup automatisé
- [ ] Scan de vulnérabilités automatique

---

## Conformité et Certifications

Cette configuration suit les recommandations de :

- ✅ **CIS Docker Benchmark**
- ✅ **OWASP Container Security**
- ✅ **Docker Security Best Practices**

---

## Support et Contribution

Pour toute question ou problème :

1. Vérifiez la section Dépannage ci-dessus
2. Consultez les logs : `./deploy-secure-ubuntu.sh logs`
3. Vérifiez le statut : `./deploy-secure-ubuntu.sh status`

---

## Licence

Ce projet est fourni "tel quel" sans garantie. Utilisez-le à vos propres risques.

---

## Crédits

Conçu par Romuald Członkowski - [www.aiadvisors.pl/en](https://www.aiadvisors.pl/en)

---

**Dernière mise à jour :** 2026-02-01
