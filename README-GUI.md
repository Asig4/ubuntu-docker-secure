# Ubuntu Docker Sécurisé avec GUI (noVNC)

## 🖥️ Vue d'ensemble

Conteneur Ubuntu 24.04 sécurisé avec **interface graphique complète** accessible via navigateur web (noVNC). Pas besoin de client VNC !

### Caractéristiques GUI

✅ **Bureau XFCE** - Interface de bureau légère et moderne
✅ **Accès Web (noVNC)** - Connexion via navigateur, aucun client à installer
✅ **Résolution HD** - 1920x1080 par défaut, configurable
✅ **Firefox inclus** - Navigateur web pré-installé
✅ **Applications** - Terminal, gestionnaire de fichiers, éditeur de texte

### Sécurité Maintenue

✅ Utilisateur non-root (appuser:1001)
✅ Isolation réseau (subnet privé 10.10.0.0/16)
✅ Volume persistant 60GB sur /data
✅ Capabilities Linux minimales
✅ Health checks actifs

---

## 🚀 Installation Rapide

### Démarrage en 2 commandes

```bash
# 1. Rendre le script exécutable
chmod +x deploy-gui.sh

# 2. Démarrer le conteneur
./deploy-gui.sh start
```

Le script affichera les informations d'accès :

```
╔════════════════════════════════════════════════════════════╗
║                  INFORMATIONS D'ACCÈS                      ║
╚════════════════════════════════════════════════════════════╝

🌐 Accès Web (noVNC) :
   URL : http://localhost:6080

🔐 Mot de passe VNC :
   Configuré dans docker-compose.gui.yml (VNC_PASSWORD)
   CHANGEZ-LE avant d'exposer sur internet !
```

### Accès à l'interface

1. Ouvrez votre navigateur web
2. Allez sur `http://localhost:6080`
3. Cliquez sur "Connect"
4. Entrez le mot de passe VNC (défini dans docker-compose.gui.yml)
5. Vous voilà sur le bureau XFCE !

**Ou utilisez la commande :**
```bash
./deploy-gui.sh open  # Ouvre automatiquement le navigateur
```

---

## 📋 Structure des Fichiers

```
.
├── Dockerfile.gui              # Image Ubuntu avec GUI
├── docker-compose.gui.yml      # Configuration GUI
├── deploy-gui.sh               # Script de gestion GUI
├── README-GUI.md               # Cette documentation
└── data/                       # Volume 60GB persistant
```

---

## 🎮 Utilisation

### Commandes Principales

```bash
# Démarrer le conteneur
./deploy-gui.sh start

# Arrêter le conteneur
./deploy-gui.sh stop

# Redémarrer le conteneur
./deploy-gui.sh restart

# Voir les logs
./deploy-gui.sh logs

# Afficher le statut et les URLs
./deploy-gui.sh status

# Ouvrir l'interface dans le navigateur
./deploy-gui.sh open
```

### Accès au Bureau

**Via Navigateur Web (Recommandé) :**
- URL : `http://localhost:6080`
- Avantages : Aucun client à installer, fonctionne partout
- Connexion : Cliquez sur "Connect" → Entrez le mot de passe

**Via Client VNC (Optionnel) :**
- Hôte : `localhost`
- Port : `5901`
- Mot de passe : Celui défini dans docker-compose.gui.yml
- Clients VNC : RealVNC, TigerVNC, TightVNC, Remmina

### Applications Pré-installées

**Déjà disponibles :**
- 🌐 **Firefox** - Navigateur web
- 💻 **XFCE Terminal** - Terminal Linux
- 📁 **Thunar** - Gestionnaire de fichiers
- 📝 **Mousepad** - Éditeur de texte

**Accès au terminal :**
1. Cliquez sur l'icône "Terminal Emulator" dans la barre du bas
2. Ou : Menu Applications → Terminal Emulator

---

## ⚙️ Configuration

### Changer le Mot de Passe VNC

**Méthode 1 : Avant le démarrage**

Éditez `docker-compose.gui.yml` :
```yaml
environment:
  - VNC_PASSWORD=VotreNouveauMotDePasse  # Changez ici
```

**Méthode 2 : Conteneur en cours d'exécution**
```bash
docker exec -it ubuntu-secure-gui bash
echo "nouveau_mot_de_passe" | vncpasswd -f > ~/.vnc/passwd
chmod 600 ~/.vnc/passwd
./deploy-gui.sh restart
```

### Changer la Résolution

Éditez `docker-compose.gui.yml` :
```yaml
environment:
  - VNC_RESOLUTION=1920x1080  # Changez la résolution
```

Résolutions communes :
- `1920x1080` - Full HD (par défaut)
- `1280x720` - HD
- `2560x1440` - 2K
- `3840x2160` - 4K

Redémarrez après modification :
```bash
./deploy-gui.sh restart
```

### Installer des Applications Supplémentaires

**Depuis le terminal du bureau :**
```bash
# Exemple : installer VSCode
sudo apt-get update
sudo apt-get install -y code

# Exemple : installer LibreOffice
sudo apt-get install -y libreoffice

# Exemple : installer GIMP
sudo apt-get install -y gimp
```

**Ou modifiez `Dockerfile.gui`** pour les inclure à l'image :
```dockerfile
RUN apt-get install -y --no-install-recommends \
    code \
    libreoffice \
    gimp
```

Puis rebuild :
```bash
./deploy-gui.sh restart
```

### Exposer sur Internet (avec précaution !)

⚠️ **ATTENTION : Sécurité Critique !**

Si vous voulez accéder au bureau depuis l'extérieur :

**1. Changez OBLIGATOIREMENT le mot de passe VNC**
```yaml
environment:
  - VNC_PASSWORD=UnMotDePasseTresComplexeEtSecurise123!@#
```

**2. Utilisez un reverse proxy avec HTTPS (Nginx, Caddy, Traefik)**
```nginx
server {
    listen 443 ssl;
    server_name votre-domaine.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:6080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**3. Ajoutez une authentification supplémentaire**
- Utilisez un VPN (Tailscale, WireGuard)
- Ajoutez une authentification HTTP basic
- Limitez l'accès par IP

**4. N'exposez JAMAIS directement le port 6080 sur internet sans HTTPS !**

---

## 🔧 Dépannage

### Le bureau ne s'affiche pas

```bash
# Vérifier que le conteneur est healthy
./deploy-gui.sh status

# Vérifier les logs
./deploy-gui.sh logs

# Vérifier que les ports sont bien exposés
docker port ubuntu-secure-gui
```

### "Connection Failed" dans noVNC

**Causes possibles :**
1. Le conteneur n'est pas démarré → `./deploy-gui.sh start`
2. Le serveur VNC n'a pas fini de démarrer → Attendez 30 secondes
3. Le port est déjà utilisé → Changez le port dans docker-compose.gui.yml

**Vérifier les ports :**
```bash
# Vérifier si le port 6080 est utilisé
lsof -i :6080

# Ou sur Linux
netstat -tuln | grep 6080
```

### Écran noir après connexion

```bash
# Redémarrer le serveur VNC
docker exec ubuntu-secure-gui pkill Xvnc
./deploy-gui.sh restart
```

### Performances lentes

**Solutions :**

1. Réduire la résolution :
```yaml
environment:
  - VNC_RESOLUTION=1280x720  # Au lieu de 1920x1080
```

2. Augmenter les ressources allouées :
```yaml
deploy:
  resources:
    limits:
      cpus: '6.0'     # Au lieu de 4.0
      memory: 12G     # Au lieu de 8G
```

3. Fermer les applications inutilisées dans le bureau

### Le clavier ne fonctionne pas correctement

Dans l'interface noVNC :
1. Cliquez sur l'icône ⚙️ (Settings) en haut à gauche
2. Activez "Show Keyboard"
3. Utilisez le clavier virtuel si nécessaire

---

## 💾 Gestion des Données

### Volume Persistant

Le répertoire `/data` dans le conteneur est persistant :

```bash
# Depuis l'hôte
ls -la ./data/

# Depuis le bureau (via Terminal)
ls -la /data/
```

**Tous les fichiers dans `/data` survivent aux redémarrages et suppressions du conteneur.**

### Sauvegarder le Bureau

**Sauvegarder la configuration XFCE :**
```bash
docker exec ubuntu-secure-gui tar -czf /data/xfce-backup.tar.gz /home/appuser/.config/xfce4
```

**Restaurer :**
```bash
docker exec ubuntu-secure-gui tar -xzf /data/xfce-backup.tar.gz -C /
```

### Transférer des Fichiers

**Via le gestionnaire de fichiers Thunar :**
1. Ouvrez Thunar depuis le bureau
2. Naviguez vers `/data`
3. Glissez-déposez vos fichiers

**Via la ligne de commande :**
```bash
# Copier vers le conteneur
docker cp fichier.txt ubuntu-secure-gui:/data/

# Copier depuis le conteneur
docker cp ubuntu-secure-gui:/data/fichier.txt ./
```

---

## 🔒 Sécurité GUI

### Meilleures Pratiques

✅ **Changez le mot de passe VNC par défaut**
✅ **N'exposez JAMAIS le port 6080 directement sur internet**
✅ **Utilisez HTTPS via un reverse proxy si accès distant**
✅ **Limitez l'accès par IP ou VPN**
✅ **Surveillez les logs régulièrement**

### Analyse de Sécurité

```bash
# Scanner l'image pour vulnérabilités
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy:latest image asig-ubuntu-secure-gui

# Vérifier l'utilisateur
docker exec ubuntu-secure-gui whoami
# Doit retourner: appuser (non-root)
```

---

## 📊 Monitoring

### Utilisation des Ressources

```bash
# Stats en temps réel
docker stats ubuntu-secure-gui

# Utilisation disque du volume
docker exec ubuntu-secure-gui du -sh /data

# Processus en cours
docker exec ubuntu-secure-gui ps aux
```

### Logs du Serveur VNC

```bash
# Logs du serveur VNC
docker exec ubuntu-secure-gui cat /home/appuser/.vnc/*.log

# Logs noVNC
./deploy-gui.sh logs | grep novnc
```

---

## 🎯 Cas d'Usage

### Développement à Distance

Installez votre IDE préféré :
```bash
# VSCode
sudo apt-get install -y code

# PyCharm Community
sudo snap install pycharm-community --classic

# Sublime Text
wget -qO - https://download.sublimetext.com/sublimehq-pub.gpg | sudo apt-key add -
sudo apt-get install sublime-text
```

### Navigation Web Isolée

Firefox est pré-installé. Utilisez-le pour :
- Tester des sites web dans un environnement isolé
- Navigation sécurisée (tout est dans le conteneur)
- Tests de compatibilité

### Environnement de Test

- Testez des applications GUI Linux
- Essayez des configurations sans risque
- Supprimez et recréez facilement

---

## 📈 Comparaison avec Version CLI

| Fonctionnalité | CLI (Dockerfile) | GUI (Dockerfile.gui) |
|----------------|------------------|----------------------|
| Taille image | ~75MB | ~850MB |
| RAM au repos | ~672KB | ~2-3GB |
| Accès | Shell uniquement | Bureau complet + Shell |
| Applications | À installer | XFCE + Firefox inclus |
| Cas d'usage | Services backend | Développement, navigation |
| Ports exposés | Aucun | 6080 (noVNC), 5901 (VNC) |

---

## 🚧 Limitations Connues

- **Taille de l'image** : ~850MB (vs ~75MB pour CLI)
- **Utilisation RAM** : 2-3GB minimum (vs <1MB pour CLI)
- **Pas de son** : Audio non supporté par défaut
- **Performances** : Légère latence sur connexions lentes

---

## 🔄 Migration CLI → GUI

Si vous avez déjà le conteneur CLI et voulez passer au GUI :

```bash
# 1. Sauvegarder les données
cp -r ./data ./data-backup

# 2. Arrêter le conteneur CLI
./deploy-secure-ubuntu.sh stop

# 3. Démarrer le conteneur GUI
./deploy-gui.sh start

# 4. Les données dans ./data sont automatiquement disponibles
```

Les deux versions peuvent coexister avec des noms différents.

---

## 🆘 Support

### Problèmes Courants

| Problème | Solution |
|----------|----------|
| Port 6080 déjà utilisé | Changez le port dans docker-compose.gui.yml |
| Écran noir | Redémarrez avec `./deploy-gui.sh restart` |
| Mot de passe refusé | Vérifiez VNC_PASSWORD dans docker-compose.gui.yml |
| Performances lentes | Réduisez la résolution ou augmentez les ressources |

---

## 📝 Changelog

### Version 2.0-gui (2026-02-01)
- ✅ Ajout interface graphique XFCE
- ✅ Accès web via noVNC (port 6080)
- ✅ Firefox pré-installé
- ✅ Scripts de gestion automatisés
- ✅ Sécurité maintenue (utilisateur non-root)

---

**Conçu par :** Romuald Członkowski - [www.aiadvisors.pl/en](https://www.aiadvisors.pl/en)

**Dernière mise à jour :** 2026-02-01
