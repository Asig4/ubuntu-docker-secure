# =============================================================================
# Dockerfile Ubuntu Sécurisé - Multi-langage Optimisé
# Base: Ubuntu 24.04 Minimal
# Priorité: Sécurité Maximale
# Volume: 60GB persistant sur /data
# Isolation: Réseau partiel avec accès internet
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base - Configuration système minimale
# -----------------------------------------------------------------------------
FROM ubuntu:24.04 AS base

# Métadonnées
LABEL maintainer="votre-email@example.com"
LABEL description="Ubuntu sécurisé multi-langage avec isolation réseau"
LABEL version="1.0"
LABEL security.level="maximum"

# Variables d'environnement pour optimisation
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC

# Mise à jour système et installation des outils de sécurité de base uniquement
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        tzdata && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \
    # Suppression des fichiers inutiles pour réduire la surface d'attaque
    rm -rf /usr/share/doc/* \
           /usr/share/man/* \
           /usr/share/info/* \
           /var/cache/apt/archives/*

# -----------------------------------------------------------------------------
# Stage 2: Security - Configuration de sécurité et utilisateur non-root
# -----------------------------------------------------------------------------
FROM base AS security

# Création de l'utilisateur non-root avec UID/GID fixes
RUN groupadd -r -g 1001 appuser && \
    useradd -r -u 1001 -g appuser -m -d /home/appuser -s /bin/bash appuser && \
    chmod 700 /home/appuser

# Création du point de montage pour le volume de données
RUN mkdir -p /data && \
    chown -R appuser:appuser /data && \
    chmod 700 /data

# Configuration du système de fichiers pour sécurité
# Création de tmpfs points (seront montés au runtime)
RUN mkdir -p /tmp /var/tmp && \
    chmod 1777 /tmp /var/tmp

# Hardening du système
RUN echo "* hard core 0" >> /etc/security/limits.conf && \
    echo "* soft core 0" >> /etc/security/limits.conf && \
    chmod 644 /etc/passwd /etc/group && \
    chmod 600 /etc/shadow && \
    find /bin /usr/bin -type f -executable -exec chmod 755 {} \; 2>/dev/null || true

# -----------------------------------------------------------------------------
# Stage 3: Final - Image finale minimale
# -----------------------------------------------------------------------------
FROM security AS final

# Variables d'environnement pour l'utilisateur
ENV HOME=/home/appuser \
    USER=appuser \
    PATH=/home/appuser/.local/bin:$PATH

# Basculement vers utilisateur non-root
USER appuser
WORKDIR /home/appuser

# Volume pour les données persistantes (60GB)
VOLUME ["/data"]

# Health check pour surveiller l'état du conteneur
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD test -d /data && test -w /data || exit 1

# Point d'entrée par défaut - garde le conteneur en vie
# À personnaliser selon vos besoins applicatifs
CMD ["tail", "-f", "/dev/null"]

# Labels de sécurité
LABEL security.scan.date="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      security.non-root="true" \
      security.read-only-root="supported" \
      security.capabilities="minimal"
