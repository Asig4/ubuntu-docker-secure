# API Watchlist Manager

> Documentation complète de l'API REST FastAPI pour la gestion des watchlists.

## Base URL

```
# En développement (accès direct)
http://localhost:8000/api/v1

# En production (via Nginx)
https://ton-domaine.com/api/v1
```

## Authentification

Toutes les routes (sauf `/health`) nécessitent un JWT token.

```
Header: Authorization: Bearer <jwt_token>
```

### Obtenir un token

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "antoine",
  "password": "ton-mot-de-passe"
}
```

**Réponse** :
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

---

## Endpoints

### Health Check

```http
GET /health
```

**Réponse** :
```json
{
  "status": "healthy",
  "database": "connected",
  "uptime": "4h 23m",
  "version": "1.0.0"
}
```

---

### Watchlists

#### Lister les watchlists d'un utilisateur

```http
GET /api/v1/watchlists
Authorization: Bearer <token>
```

**Réponse** :
```json
{
  "watchlists": [
    {
      "id": 1,
      "name": "Crypto Majeurs",
      "assets": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT"],
      "is_default": true,
      "created_at": "2026-02-12T10:00:00Z",
      "updated_at": "2026-02-12T14:30:00Z"
    },
    {
      "id": 2,
      "name": "US Stocks",
      "assets": ["AAPL", "MSFT", "TSLA", "NVDA", "GOOGL"],
      "is_default": false,
      "created_at": "2026-02-12T10:30:00Z",
      "updated_at": "2026-02-12T10:30:00Z"
    }
  ],
  "total": 2
}
```

#### Créer une watchlist

```http
POST /api/v1/watchlists
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Mon portefeuille",
  "assets": ["BTC/USDT", "ETH/USDT", "AAPL", "EUR/USD"],
  "is_default": false
}
```

**Réponse** (201 Created) :
```json
{
  "id": 3,
  "name": "Mon portefeuille",
  "assets": ["BTC/USDT", "ETH/USDT", "AAPL", "EUR/USD"],
  "is_default": false,
  "created_at": "2026-02-12T15:00:00Z"
}
```

**Validations** :
- `name` : 1-100 caractères, unique par utilisateur
- `assets` : tableau de 1 à 100 assets
- Chaque asset doit être un symbol valide (vérifié contre la liste supportée)

#### Modifier une watchlist

```http
PUT /api/v1/watchlists/{id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Crypto Majeurs v2",
  "assets": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT", "DOT/USDT"]
}
```

**Réponse** (200 OK) :
```json
{
  "id": 1,
  "name": "Crypto Majeurs v2",
  "assets": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT", "DOT/USDT"],
  "is_default": true,
  "updated_at": "2026-02-12T15:05:00Z"
}
```

#### Supprimer une watchlist

```http
DELETE /api/v1/watchlists/{id}
Authorization: Bearer <token>
```

**Réponse** (204 No Content)

**Contrainte** : impossible de supprimer la watchlist par défaut si c'est la dernière.

---

### Assets

#### Rechercher un asset

```http
GET /api/v1/assets/search?q=bitcoin&type=crypto
Authorization: Bearer <token>
```

**Paramètres** :
| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Terme de recherche (nom, symbol) |
| `type` | string | Filtre par type : `crypto`, `stock`, `forex`, `commodity`, `index` |
| `exchange` | string | Filtre par exchange : `binance`, `yahoo`, `coingecko` |
| `limit` | int | Max résultats (défaut: 20, max: 100) |

**Réponse** :
```json
{
  "results": [
    {
      "symbol": "BTC/USDT",
      "name": "Bitcoin",
      "type": "crypto",
      "exchanges": ["binance", "coingecko"],
      "market_cap_rank": 1
    },
    {
      "symbol": "BTC/EUR",
      "name": "Bitcoin (EUR)",
      "type": "crypto",
      "exchanges": ["binance"],
      "market_cap_rank": 1
    }
  ],
  "total": 2
}
```

#### Lister les assets actuellement suivis

```http
GET /api/v1/assets/active
Authorization: Bearer <token>
```

Retourne l'union de tous les assets de toutes les watchlists actives (utilisé par le Market Feeder).

**Réponse** :
```json
{
  "active_assets": [
    {"symbol": "BTC/USDT", "type": "crypto", "exchanges": ["binance"]},
    {"symbol": "ETH/USDT", "type": "crypto", "exchanges": ["binance"]},
    {"symbol": "AAPL", "type": "stock", "exchanges": ["yahoo"]},
    {"symbol": "EUR/USD", "type": "forex", "exchanges": ["yahoo"]}
  ],
  "total": 4,
  "last_updated": "2026-02-12T15:00:00Z"
}
```

---

## Codes d'erreur

| Code | Signification | Exemple |
|------|--------------|---------|
| 200 | Succès | Requête OK |
| 201 | Créé | Watchlist créée |
| 204 | Supprimé | Watchlist supprimée |
| 400 | Requête invalide | JSON malformé, asset invalide |
| 401 | Non authentifié | Token manquant ou expiré |
| 403 | Non autorisé | Pas propriétaire de la watchlist |
| 404 | Non trouvé | Watchlist inexistante |
| 409 | Conflit | Nom de watchlist déjà existant |
| 422 | Validation échouée | Champ obligatoire manquant |
| 429 | Rate limited | Trop de requêtes (100/min) |
| 500 | Erreur serveur | Bug, BDD down |

**Format d'erreur** :
```json
{
  "detail": {
    "code": "WATCHLIST_NOT_FOUND",
    "message": "La watchlist avec l'ID 99 n'existe pas",
    "timestamp": "2026-02-12T15:00:00Z"
  }
}
```

## Rate Limiting

- **100 requêtes par minute** par utilisateur
- Header de réponse : `X-RateLimit-Remaining: 87`
- En cas de dépassement : HTTP 429 avec `Retry-After: 30`

## Documentation interactive

FastAPI génère automatiquement une documentation interactive :

- **Swagger UI** : `http://localhost:8000/docs`
- **ReDoc** : `http://localhost:8000/redoc`
- **OpenAPI JSON** : `http://localhost:8000/openapi.json`
