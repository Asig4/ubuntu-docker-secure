# Memory - Projet Burot-Sigoignet

## Deploiement Hostinger
- SSH: `ssh -p 65002 u275525936@185.224.137.134` (alias: `burot-sigoignet` ou `wonmas`)
- Theme path: `/home/u275525936/domains/burot-sigoignet.com/public_html/wp-content/themes/burot-sigoignet-theme/`
- WP-CLI: `/usr/local/bin/wp` (pas wp-cli.phar)
- WP user: `asigoignet1@gmail.com` (ID 1)
- WP app password (Claude-MCP): regenerer via `wp user application-password create 1 'Claude-MCP' --porcelain`
- **Wordfence**: `loginSec_disableApplicationPasswords` doit etre a 0 pour que les app passwords marchent
- SMTP Hostinger: `smtp.hostinger.com:465` SSL
- Emails Hostinger: `portail-famille@burot-sigoignet.com`, `antoine@burot-sigoignet.com`, `noreply@burot-sigoignet.com`
- **Hostinger API MCP**: `npx hostinger-api-mcp@latest` (dans Claude Desktop)

## Infrastructure Tailscale
- **Mac-mini** (WONMAS): TS `100.83.109.123` / LAN `192.168.10.100` / SSH: `ssh -i ~/.ssh/id_ed25519 serveurwonmas@100.83.109.123`
- **QNAP-NAS** (amgf-hk): TS `100.65.136.110` / LAN `192.168.10.101` / SSH user `Admin-Antoine` / MCP port 8442
- **QNAP-TH** (amigofriends): TS `100.68.144.1` / MCP port 8442
- **MacBook Pro**: TS `100.114.118.110`
- **RTX** (PC gaming): LAN `192.168.10.126` / SSH user `as`
- **RPi**: LAN `192.168.10.109` / SSH user `as`
- **NUC**: LAN `192.168.10.115` / SSH user `as`
- **TV**: LAN `192.168.10.189` / SSH user `tv` / key `id_ed25519_papa_tv`
- **moltbot** (Parallels VM): `10.211.55.12:29211` / SSH user `asbot1`
- IP publique mac-mini: `77.196.63.153` (Free FR) - port forwarding 443 casse, utiliser Tailscale
- `/etc/hosts` local: `100.83.109.123 n8n.wonmas.com` (bypass port forwarding casse)

## n8n (Mac-mini Docker)
- URL: `https://n8n.wonmas.com` (via Traefik reverse proxy)
- MCP endpoint: `https://n8n.wonmas.com/mcp-server/http` (streamableHttp)
- Login: `asigoignet1@gmail.com` / `Admin1138!`
- Docker compose: `/Users/serveurwonmas/docker/n8n/docker-compose.yml`
- Docker: `/usr/local/bin/docker` (PAS dans le PATH par defaut)
- DB: SQLite `/home/node/.n8n/database.sqlite` (dans le container)
- SMTP: `noreply@burot-sigoignet.com` via `smtp.hostinger.com:465` SSL
- MCP token JWT: sans expiration (pas de champ `exp`)
- **Gotcha docker cp**: apres `docker cp` dans le container, toujours `chown node:node` + `chmod 644` sur le fichier
- Traefik: file provider (PAS docker labels), config dans `/etc/traefik/config/n8n.yml`
- Let's Encrypt cert valide, certResolver: `letsencrypt`

## Claude Desktop MCP Config
- Config: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Logs: `~/Library/Logs/Claude/mcp-server-*.log` et `mcp.log`
- MCP servers s'initialisent a la demande (lazy loading en mode Cowork)
- **hostinger-mcp**: `npx hostinger-api-mcp@latest` + API token
- **tailscale MCP**: `npx @hexsleeves/tailscale-mcp-server` + `LOG_LEVEL=3` + `NODE_ENV=production` (sinon erreur JSON parse)
- **wordpress-burot MCP**: `mcp-remote` + Basic auth (app password WP) -> endpoint `/wp-json/mcp/mcp-adapter-default-server`
- **QNAP-NAS MCP**: `mcp-remote` + `--allow-http` + Bearer token -> `http://100.65.136.110:8442/sse`
- **QNAP-TH MCP**: `mcp-remote` + `--allow-http` + Bearer token -> `http://100.68.144.1:8442/sse`
- **n8n MCP**: `supergateway` + `--streamableHttp` + Bearer JWT -> `https://n8n.wonmas.com/mcp-server/http`

## Claude Code MCP Config
- Global (`~/.claude.json` > mcpServers): `n8n-mcp` (stdio, `npx n8n-mcp`), `MCP_DOCKER` (`docker mcp gateway run`)
- Projet `/Users/asig` (`.claude.json` > projects): `wordpress-com` (HTTP, public-api.wordpress.com), `burot-sigoignet` (stdio, `/Users/asig/.local/bin/burot-sigoignet-mcp`)

## Lecons SCP
- **IMPORTANT**: `scp` avec plusieurs fichiers vers un dossier met TOUT au meme endroit. Ne pas melanger fichiers de sous-dossiers differents dans un seul scp.
- Toujours uploader vers le bon sous-dossier: `assets/css/`, `inc/`, `inc/api/`, etc.

## Cache LiteSpeed
- Bumper `BS_THEME_VERSION` (functions.php) + `Version:` (style.css) apres modif CSS/JS
- Browser cache par `?ver=X.X.X` — purge seule ne suffit pas, verifier avec `fetch()` + `Date.now()`
- Purge: `wp litespeed-purge all`
- **Reload fix**: `window.location.reload()` sert du cache LS → utiliser `reloadPage()` avec `?t=Date.now()`
- Applique dans: tasks.js, calendar.js, budget.js, documents.js, emails.js, bottom-nav.js

## Capabilities WordPress
- Les capabilities sont ajoutees via `bs_create_custom_roles()` sur `after_setup_theme`
- Nouvelles capabilities necessitent parfois un ajout manuel: `wp cap add administrator bs_xxx`
- Verifier: `wp cap list administrator | grep bs_`
- **OR logic**: `current_user_can()` ne supporte pas les arrays. Utiliser un helper custom (ex: `bs_user_has_nav_cap`)
- **Settings page**: visible si `bs_manage_portal_settings` (admin) OU `bs_send_emails` (parent) - aligner sidebar ET bottom nav
- Parents (bs_parent): ont `bs_send_emails` mais PAS `bs_manage_portal_settings`

## Design Glassmorphism Minimal
- Blur: 10px, glass opacity: 6%, border opacity: 10%, border-radius: 12px
- Gradient: #334155 -> #1e293b -> #0f172a
- Dark mode force (data-theme="dark"), pas de toggle
- Modal: blur 20px, background rgba(15,23,42,0.95), border-radius 16px

## PWA Implementation
- SW servi depuis racine via `/?bs-sw` hook PHP dans functions.php (scope `/`)
- Cache: assets statiques uniquement (Cache-First), HTML = Network-Only (site prive)
- Manifest: `manifest.json` a la racine du theme
- Offline: `offline.html` glassmorphism
- Icones: `icon-192.png` et `icon-512.png` dans `assets/img/`
- Meta: `mobile-web-app-capable` (PAS `apple-mobile-web-app-capable` = deprecie)
- Version cache: `bs-portal-v1` - bumper dans `service-worker.js` si changement assets

## Architecture Theme
- Voir `/Users/asig/Projects/burot-sigoignet-theme/CLAUDE.md` pour doc complete
- **Version actuelle: 1.29.0**
- Core: logger.php, rate-limiter.php, security.php, login.php (custom login page)
- Modules: calendar, tasks, contacts, budget, documents, wiki, emails, feedback, **weather**, **activity**
- Templates: page-dashboard, page-calendar, page-contacts, page-documents, page-emails, page-budget, page-wiki, page-settings, page-profile, page-welcome, page-login, archive-task, single-task
- API (14 endpoints): tasks, calendar, contacts, budget, documents, emails, wiki-suggestions, feedback, search, notifications, settings, dashboard-widgets, bottom-nav, webhooks
- JS (18 fichiers): tasks.js (30K), emails.js (24K), calendar.js, budget.js, documents.js, wiki.js, contacts.js, settings.js, shortcuts.js, notifications.js, dashboard-config.js, bottom-nav.js, feedback.js, toast.js, confirm.js, utils.js, theme.js, dashboard.js
- CSS: pages.css (101K), components.css (16K), layout.css, variables.css, base.css
- Module guards: calendar/guards.php, documents/guards.php, contacts/guards.php

## Module Details (CPTs & Gotchas)
- **Feedback**: CPT `bs_feedback` (types: bug/suggestion/question, status: new/reviewed/resolved), FAB dans footer.php, API: POST (any user), GET/PATCH (admin)
- **Budget**: CPT `bs_budget_entry` (meta: amount, date, category, type, recurring), 8 categories, objectifs `bs_budget_targets` (JSON), mois FR via tableau PHP (strftime deprecie PHP 8), template CSV dans assets/
- **Contacts**: CPT `bs_contact` + REST API CRUD + modal inline + guards
- **Calendar**: ICS read + CPT `bs_event` local CRUD + modal + grille mensuelle + guards
- **Tasks**: CPT `task` + REST API CRUD + filtres + kanban D&D + modal + recurring + templates + export CSV
- **Documents**: Coffre-fort `wp-content/bs-vault/` (.htaccess deny + noms random 8 chars + 0640), download proxy API, upload max 50MB
- **Emails**: IMAP client + REST API + inbox + compose/reply + settings IMAP par user
- **Weather**: API meteo externe
- **Activity**: Tracker d'activite utilisateur

## Documents Coffre-Fort (Details)
- Stockage: `wp-content/bs-vault/` (PAS uploads/) + `.htaccess` deny + `index.php` silencieux
- Fichiers: 0640, noms random 8 chars, acces direct = 403
- Download: `GET /bs/v1/documents/{id}/download` (auth + nonce), PDFs/images inline, autres force download
- Upload: `bs_vault_upload()` max 50MB, `wp_check_filetype`
- Meta: bs_vault_filename, bs_vault_size, bs_original_filename, bs_doc_category, bs_doc_description, bs_uploaded_by

## i18n System (v1.17.0)
- Systeme leger: tableaux PHP, pas de .po/.mo, pas de plugin
- 3 langues: FR (defaut), EN, TH — ~490 cles par langue, ~127 exposees au JS
- Helper: `bs_t('key')` avec fallback FR, vsprintf pour variables
- Detection: URL `?lang=xx` > user_meta `bs_lang` > cookie `bs_lang` > 'fr'
- Fichiers: `inc/i18n.php`, `languages/fr.php`, `languages/en.php`, `languages/th.php`
- JS: `BS.i18n['key']` et `BS.lang` via wp_localize_script
- Switcher: dropdown `.bs-lang-switcher` dans topbar.php
- Hook `init` priority 5 pour detection langue avant tout le reste
- Mois: `bs_t('cal.months').split(',')` en JS / Categories budget: `bs_t('cat.' . $category)`

## Bottom Nav Configurable (v1.23.0)
- Registre: `inc/bottom-nav.php` avec `bs_get_available_nav_items()` (10 items)
- API: GET/POST `/bs/v1/bottom-nav` dans `inc/api/bottom-nav.php`
- JS: `assets/js/bottom-nav.js` (bottom sheet + pin/unpin + API save)
- Stockage: user_meta `bs_bottom_nav_items` (array max 4 IDs)
- Default admin/parent: [dashboard, calendar, tasks, wiki], child: [dashboard, tasks, wiki, profile]
- Bouton Plus (5e position) ouvre bottom sheet avec TOUTES les pages
- Pin/unpin via etoile, max 4, toast si depassement
- **Capability OR**: settings utilise array `['bs_manage_portal_settings', 'bs_send_emails']`
- Helper `bs_user_has_nav_cap($user, $cap)` supporte string OU array (OR logic)
- Template: `template-parts/navigation/bottom-nav.php` (dynamique, plus hardcode)
- CSS: `.bs-bottom-sheet` dans `components.css` (slide-up, backdrop, swipe-down close)
- i18n: nav.more, nav.pin, nav.unpin, nav.max_pinned, nav.configure (FR/EN/TH)

## Tasks - Recurring Generation Gotcha
- Le trigger `bs_generate_next_recurring_task()` doit etre dans PATCH /status ET PUT (modal edit)
- Bug v1.21.0: seul PATCH /status avait le trigger, pas PUT -> corrige dans v1.22.0

## Tasks CPT - Enforce Assignee Gotcha
- `bs_task_enforce_assignee` force les tasks en draft si pas d'assignee
- Via WP-CLI: les meta sont ajoutees APRES `wp post create`, donc la task passe en draft
- Solution API REST: `remove_action('save_post', 'bs_task_enforce_assignee', 10)` avant `wp_insert_post`
- Via WP-CLI: creer le post, ajouter les meta, puis `wp post update --post_status=publish`
