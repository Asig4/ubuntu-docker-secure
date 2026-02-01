#!/bin/bash
# =============================================================================
# Script de déploiement du conteneur Ubuntu sécurisé
# Usage: ./deploy-secure-ubuntu.sh [start|stop|restart|logs|status]
# =============================================================================

set -euo pipefail

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="ubuntu-secure-app"
DATA_DIR="./data"
COMPOSE_FILE="docker-compose.yml"

# Fonction d'affichage
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Vérification des prérequis
check_prerequisites() {
    print_status "Vérification des prérequis..."

    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker n'est pas installé"
        exit 1
    fi

    # Vérifier Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose n'est pas installé"
        exit 1
    fi

    # Vérifier les fichiers nécessaires
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        print_error "Fichier $COMPOSE_FILE introuvable"
        exit 1
    fi

    if [[ ! -f "Dockerfile" ]]; then
        print_error "Fichier Dockerfile introuvable"
        exit 1
    fi

    print_status "Prérequis OK"
}

# Créer le répertoire de données
setup_data_directory() {
    print_status "Configuration du répertoire de données..."

    if [[ ! -d "$DATA_DIR" ]]; then
        mkdir -p "$DATA_DIR"
        chmod 700 "$DATA_DIR"

        # Changer le propriétaire si possible (nécessite sudo)
        if [[ $EUID -ne 0 ]]; then
            print_warning "Exécutez avec sudo pour définir les bonnes permissions"
            print_warning "sudo chown -R 1000:1000 $DATA_DIR"
        else
            chown -R 1000:1000 "$DATA_DIR"
        fi

        print_status "Répertoire de données créé: $DATA_DIR"
    else
        print_status "Répertoire de données existe déjà: $DATA_DIR"
    fi
}

# Créer le réseau si nécessaire
setup_network() {
    print_status "Configuration du réseau sécurisé..."
    # Docker Compose créera le réseau automatiquement avec la config du yml
    print_status "Le réseau sera créé par Docker Compose"
}

# Démarrer le conteneur
start_container() {
    print_status "Démarrage du conteneur..."

    check_prerequisites
    setup_data_directory
    setup_network

    # Build et démarrage
    docker-compose up -d --build

    # Attendre que le conteneur soit healthy
    print_status "Attente du démarrage du conteneur..."
    local max_wait=30
    local waited=0

    while [[ $waited -lt $max_wait ]]; do
        if docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null | grep -q "healthy"; then
            print_status "Conteneur démarré avec succès!"
            show_status
            return 0
        fi

        sleep 1
        waited=$((waited + 1))
    done

    print_warning "Le conteneur a démarré mais n'est pas encore healthy"
    show_status
}

# Arrêter le conteneur
stop_container() {
    print_status "Arrêt du conteneur..."
    docker-compose down
    print_status "Conteneur arrêté"
}

# Redémarrer le conteneur
restart_container() {
    print_status "Redémarrage du conteneur..."
    stop_container
    sleep 2
    start_container
}

# Afficher les logs
show_logs() {
    print_status "Logs du conteneur (Ctrl+C pour quitter):"
    docker-compose logs -f
}

# Afficher le statut
show_status() {
    print_status "Statut du conteneur:"
    echo ""

    if docker ps --format '{{.Names}}' | grep -q "$CONTAINER_NAME"; then
        echo -e "${GREEN}✓${NC} Conteneur en cours d'exécution"

        # Informations détaillées
        echo ""
        echo "ID: $(docker ps --filter name=$CONTAINER_NAME --format '{{.ID}}')"
        echo "Image: $(docker ps --filter name=$CONTAINER_NAME --format '{{.Image}}')"
        echo "Status: $(docker ps --filter name=$CONTAINER_NAME --format '{{.Status}}')"
        echo "Health: $(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo 'N/A')"

        # Utilisation des ressources
        echo ""
        echo "Ressources utilisées:"
        docker stats --no-stream --format "  CPU: {{.CPUPerc}}  |  RAM: {{.MemUsage}}  |  NET: {{.NetIO}}" "$CONTAINER_NAME"

        # Taille du volume
        echo ""
        echo "Espace disque utilisé dans /data:"
        docker exec "$CONTAINER_NAME" du -sh /data 2>/dev/null || echo "  N/A"

    else
        echo -e "${RED}✗${NC} Conteneur arrêté"
    fi
}

# Exécuter une commande dans le conteneur
exec_container() {
    if docker ps --format '{{.Names}}' | grep -q "$CONTAINER_NAME"; then
        print_status "Ouverture d'un shell dans le conteneur..."
        docker exec -it "$CONTAINER_NAME" /bin/bash
    else
        print_error "Le conteneur n'est pas en cours d'exécution"
        exit 1
    fi
}

# Afficher l'aide
show_help() {
    cat << EOF
Usage: $0 [COMMAND]

Commandes disponibles:
  start     Démarrer le conteneur
  stop      Arrêter le conteneur
  restart   Redémarrer le conteneur
  logs      Afficher les logs en temps réel
  status    Afficher le statut du conteneur
  exec      Ouvrir un shell dans le conteneur
  help      Afficher cette aide

Examples:
  $0 start          # Démarrer le conteneur
  $0 logs           # Voir les logs
  $0 exec           # Ouvrir un shell
EOF
}

# Menu principal
main() {
    case "${1:-help}" in
        start)
            start_container
            ;;
        stop)
            stop_container
            ;;
        restart)
            restart_container
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        exec)
            exec_container
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Commande inconnue: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Point d'entrée
main "$@"
