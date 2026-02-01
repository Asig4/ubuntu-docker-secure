# Ubuntu Docker Sécurisé - CLI & GUI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420?style=flat&logo=ubuntu&logoColor=white)](https://ubuntu.com/)

Conteneurs Docker Ubuntu 24.04 sécurisés avec **deux versions** : CLI légère et GUI complète avec interface web noVNC.

## 🎯 Caractéristiques

### 🔒 Sécurité Maximale
- ✅ Utilisateur non-root (appuser:1001)
- ✅ Isolation réseau avec accès internet contrôlé
- ✅ Capabilities Linux minimales
- ✅ Volume persistant sécurisé (60GB)
- ✅ Health checks actifs
- ✅ Conforme CIS Docker Benchmark

### 📦 Deux Versions Disponibles

#### Version CLI (Légère)
- **Taille :** ~75MB
- **RAM :** 672KB au repos
- **Usage :** Services backend, APIs, applications sans GUI
- **Démarrage :** ~5 secondes

#### Version GUI (Complète)
- **Taille :** ~850MB
- **RAM :** 2-3GB
- **Bureau :** XFCE avec Firefox, Terminal, gestionnaire de fichiers
- **Accès :** noVNC via navigateur web (http://localhost:6080)
- **Démarrage :** ~30 secondes

## 🚀 Démarrage Rapide

### Prérequis
- Docker 20.10+
- Docker Compose 1.29+
- 60GB d'espace disque disponible

### Installation CLI

```bash
# Cloner le dépôt
git clone https://github.com/Asig4/ubuntu-docker-secure.git
cd ubuntu-docker-secure

# Démarrer la version CLI
chmod +x deploy-secure-ubuntu.sh
./deploy-secure-ubuntu.sh start

# Accéder au shell
./deploy-secure-ubuntu.sh exec
```

### Installation GUI

```bash
# Démarrer la version GUI
chmod +x deploy-gui.sh
./deploy-gui.sh start

# Accéder au bureau via navigateur
./deploy-gui.sh open
# Ou manuellement : http://localhost:6080
```

## 📊 Comparaison

| Aspect | CLI | GUI |
|--------|-----|-----|
| **Taille image** | ~75MB | ~850MB |
| **RAM utilisée** | 672KB | 2-3GB |
| **Interface** | Shell uniquement | Bureau XFCE complet |
| **Accès** | Terminal | Navigateur web (noVNC) |
| **Applications** | À installer | Firefox, Terminal, Thunar inclus |
| **Cas d'usage** | Services, APIs | Développement, navigation |

## 📁 Structure du Projet

```
ubuntu-docker-secure/
├── 📦 Version CLI
│   ├── Dockerfile                   # Image CLI sécurisée
│   ├── docker-compose.yml           # Configuration CLI
│   ├── deploy-secure-ubuntu.sh      # Script de gestion CLI
│   └── README-UBUNTU-SECURE.md      # Documentation CLI
│
├── 🖥️ Version GUI
│   ├── Dockerfile.gui.simple        # Image GUI avec XFCE + noVNC
│   ├── docker-compose.gui.yml       # Configuration GUI
│   ├── deploy-gui.sh                # Script de gestion GUI
│   └── README-GUI.md                # Documentation GUI
│
├── 🔒 Sécurité
│   ├── seccomp-default.json         # Profile Seccomp (optionnel)
│   └── DESIGN-UBUNTU-SECURE.md      # Architecture détaillée
│
├── 📄 Documentation
│   ├── README.md                    # Ce fichier
│   └── .gitignore                   # Fichiers exclus
│
└── 💾 Données (créé automatiquement)
    └── data/                        # Volume 60GB persistant
```

## 🎮 Utilisation

### Commandes CLI

```bash
./deploy-secure-ubuntu.sh start     # Démarrer
./deploy-secure-ubuntu.sh stop      # Arrêter
./deploy-secure-ubuntu.sh restart   # Redémarrer
./deploy-secure-ubuntu.sh logs      # Voir les logs
./deploy-secure-ubuntu.sh status    # Afficher le statut
./deploy-secure-ubuntu.sh exec      # Ouvrir un shell
```

### Commandes GUI

```bash
./deploy-gui.sh start               # Démarrer
./deploy-gui.sh stop                # Arrêter
./deploy-gui.sh restart             # Redémarrer
./deploy-gui.sh logs                # Voir les logs
./deploy-gui.sh status              # Afficher le statut
./deploy-gui.sh open                # Ouvrir le navigateur
```

## 🔧 Configuration

### Personnaliser les Ressources

Éditez `docker-compose.yml` ou `docker-compose.gui.yml` :

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'      # Maximum CPU
      memory: 8G       # Maximum RAM
```

### Exposer des Ports

```yaml
ports:
  - "8080:8080"  # Format: hote:conteneur
```

### Variables d'Environnement

```yaml
environment:
  - TZ=Europe/Paris
  - NODE_ENV=production
```

## 🔐 Sécurité

### Bonnes Pratiques Appliquées

✅ **Utilisateur non-root** - Toutes les opérations avec appuser:1001
✅ **Isolation réseau** - Subnet privé 10.10.0.0/16
✅ **Capabilities minimales** - ALL dropped par défaut
✅ **Read-only supporté** - Rootfs peut être en lecture seule
✅ **Health checks** - Surveillance active de l'état
✅ **Logs limités** - Rotation automatique (10MB max)

### Scan de Vulnérabilités

```bash
# Scanner l'image avec Trivy
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy:latest image asig-ubuntu-secure
```

## 📖 Documentation Complète

- **[README-UBUNTU-SECURE.md](README-UBUNTU-SECURE.md)** - Guide CLI détaillé
- **[README-GUI.md](README-GUI.md)** - Guide GUI complet avec noVNC
- **[DESIGN-UBUNTU-SECURE.md](DESIGN-UBUNTU-SECURE.md)** - Architecture et décisions techniques

## 🛠️ Dépannage

### Conteneur CLI ne démarre pas

```bash
# Vérifier les logs
./deploy-secure-ubuntu.sh logs

# Vérifier la configuration
docker-compose config
```

### Conteneur GUI - Pas d'accès

```bash
# Vérifier que les ports sont exposés
docker port ubuntu-secure-gui

# Vérifier les logs VNC
./deploy-gui.sh logs | grep vnc
```

### Problèmes de permissions sur /data

```bash
# Corriger les permissions
sudo chown -R 1001:1001 ./data/
sudo chmod 700 ./data/
```

## 🤝 Contribution

Les contributions sont les bienvenues !

1. Fork le projet
2. Créez une branche (`git checkout -b feature/amelioration`)
3. Commit vos changements (`git commit -m 'Ajout nouvelle fonctionnalité'`)
4. Push vers la branche (`git push origin feature/amelioration`)
5. Ouvrez une Pull Request

## 📝 Changelog

### Version 1.0.0 (2026-02-01)
- ✨ Version initiale
- ✅ Conteneur CLI sécurisé (~75MB)
- ✅ Conteneur GUI avec XFCE + noVNC (~850MB)
- ✅ Volume persistant 60GB
- ✅ Documentation complète
- ✅ Scripts de gestion automatisés

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 👨‍💻 Auteur

**Conçu par :** Romuald Członkowski - [www.aiadvisors.pl/en](https://www.aiadvisors.pl/en)

**Co-développé avec :** Claude Sonnet 4.5

## 🌟 Remerciements

- Ubuntu pour l'excellente distribution de base
- Docker pour la technologie de conteneurisation
- TigerVNC et noVNC pour l'accès GUI à distance
- XFCE pour l'environnement de bureau léger

## 📞 Support

- 🐛 **Issues :** [GitHub Issues](https://github.com/Asig4/ubuntu-docker-secure/issues)
- 💬 **Discussions :** [GitHub Discussions](https://github.com/Asig4/ubuntu-docker-secure/discussions)
- 📧 **Email :** l4bo@hotmail.fr

---

**⭐ Si ce projet vous est utile, n'hésitez pas à lui donner une étoile !**
