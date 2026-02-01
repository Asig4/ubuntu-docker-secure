#!/bin/bash
# =============================================================================
# Script de déploiement du conteneur Ubuntu sécurisé avec GUI (noVNC)
# Usage: ./deploy-gui.sh [start|stop|restart|logs|status]
# =============================================================================

set -euo pipefail

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="ubuntu-secure-gui"
DATA_DIR="./data"
COMPOSE_FILE="docker-compose.gui.yml"
NOVNC_PORT=6080
VNC_PORT=5901

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

print_success() {
    echo -e "${CYAN}[SUCCESS]${NC} $1"
}

# Banner
show_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║         Ubuntu Secure Container with GUI (noVNC)          ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Vérification des prérequis
check_prerequisites() {
    print_status "Vérification des prérequis..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker n'est pas installé"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose n'est pas installé"
        exit 1
    fi

    if [[ ! -f "$COMPOSE_FILE" ]]; then
        print_error "Fichier $COMPOSE_FILE introuvable"
        exit 1
    fi

    if [[ ! -f "Dockerfile.gui" ]]; then
        print_error "Fichier Dockerfile.gui introuvable"
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

        if [[ $EUID -ne 0 ]]; then
            print_warning "Exécutez avec sudo pour définir les bonnes permissions"
            print_warning "sudo chown -R 1001:1001 $DATA_DIR"
        else
            chown -R 1001:1001 "$DATA_DIR"
        fi

        print_status "Répertoire de données créé: $DATA_DIR"
    else
        print_status "Répertoire de données existe déjà: $DATA_DIR"
    fi
}

# Démarrer le conteneur
start_container() {
    show_banner
    print_status "Démarrage du conteneur avec GUI..."

    check_prerequisites
    setup_data_directory

    # Build et démarrage
    docker-compose -f "$COMPOSE_FILE" up -d --build

    # Attendre que le conteneur soit healthy
    print_status "Attente du démarrage du conteneur..."
    local max_wait=60
    local waited=0

    while [[ $waited -lt $max_wait ]]; do
        if docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null | grep -q "healthy"; then
            print_success "Conteneur démarré avec succès!"
            show_access_info
            return 0
        fi

        sleep 2
        waited=$((waited + 2))
        echo -n "."
    done

    echo ""
    print_warning "Le conteneur a démarré mais n'est pas encore healthy"
    show_access_info
}

# Afficher les informations d'accès
show_access_info() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                  INFORMATIONS D'ACCÈS                      ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}🌐 Accès Web (noVNC) :${NC}"
    echo -e "   URL : ${BLUE}http://localhost:${NOVNC_PORT}${NC}"
    echo -e "   ou  : ${BLUE}http://$(hostname -I | awk '{print $1}'):${NOVNC_PORT}${NC}"
    echo ""
    echo -e "${GREEN}🖥️  Accès VNC Direct :${NC}"
    echo -e "   Hôte : localhost"
    echo -e "   Port : ${VNC_PORT}"
    echo ""
    echo -e "${YELLOW}🔐 Mot de passe VNC :${NC}"
    echo -e "   Configuré dans docker-compose.gui.yml (VNC_PASSWORD)"
    echo -e "   ${RED}CHANGEZ-LE avant d'exposer sur internet !${NC}"
    echo ""
    echo -e "${GREEN}📁 Volume de données :${NC}"
    echo -e "   ${DATA_DIR} → /data (dans le conteneur)"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Arrêter le conteneur
stop_container() {
    print_status "Arrêt du conteneur..."
    docker-compose -f "$COMPOSE_FILE" down
    print_success "Conteneur arrêté"
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
    docker-compose -f "$COMPOSE_FILE" logs -f
}

# Afficher le statut
show_status() {
    print_status "Statut du conteneur:"
    echo ""

    if docker ps --format '{{.Names}}' | grep -q "$CONTAINER_NAME"; then
        echo -e "${GREEN}✓${NC} Conteneur en cours d'exécution"

        echo ""
        echo "ID: $(docker ps --filter name=$CONTAINER_NAME --format '{{.ID}}')"
        echo "Image: $(docker ps --filter name=$CONTAINER_NAME --format '{{.Image}}')"
        echo "Status: $(docker ps --filter name=$CONTAINER_NAME --format '{{.Status}}')"
        echo "Health: $(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo 'N/A')"

        echo ""
        echo "Ports exposés:"
        docker port "$CONTAINER_NAME"

        echo ""
        echo "Ressources utilisées:"
        docker stats --no-stream --format "  CPU: {{.CPUPerc}}  |  RAM: {{.MemUsage}}  |  NET: {{.NetIO}}" "$CONTAINER_NAME"

        echo ""
        show_access_info

    else
        echo -e "${RED}✗${NC} Conteneur arrêté"
    fi
}

# Ouvrir le navigateur
open_browser() {
    local url="http://localhost:${NOVNC_PORT}"

    print_status "Ouverture du navigateur..."

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open "$url"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v xdg-open &> /dev/null; then
            xdg-open "$url"
        else
            print_warning "Impossible d'ouvrir le navigateur automatiquement"
            echo "Ouvrez manuellement: $url"
        fi
    else
        print_warning "OS non supporté pour l'ouverture automatique"
        echo "Ouvrez manuellement: $url"
    fi
}

# Afficher l'aide
show_help() {
    cat << EOF
Usage: $0 [COMMAND]

Commandes disponibles:
  start     Démarrer le conteneur avec GUI
  stop      Arrêter le conteneur
  restart   Redémarrer le conteneur
  logs      Afficher les logs en temps réel
  status    Afficher le statut et les infos d'accès
  open      Ouvrir le navigateur sur l'interface noVNC
  help      Afficher cette aide

Exemples:
  $0 start          # Démarrer le conteneur
  $0 open           # Ouvrir l'interface web
  $0 logs           # Voir les logs
  $0 status         # Voir le statut et les URLs d'accès

Accès:
  - Interface Web : http://localhost:${NOVNC_PORT}
  - Client VNC    : localhost:${VNC_PORT}
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
        open)
            open_browser
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
