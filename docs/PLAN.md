# Build Plan — Smart City Big Data Access Lab

## Goal

A containerised lab that shows **role-based, column-aware access to a smart-city
data lake**. Synthetic Parquet files are queried live with DuckDB; a permission
grid decides, per role and per dataset, whether a caller is denied, gets
aggregates only, or gets record-level rows with each column cleared, masked,
pseudonymised, generalised or dropped. Every request is audited in a form a SIEM
can consume. Authentication is RS256-signed JWTs whose tampering is demonstrable.

## Architecture

```
 browser ──► frontend (nginx :8080) ──/api──► backend (gunicorn :8000)
                                               │  Django + DRF + SimpleJWT(RS256)
                                               │  permission grid (Postgres)
                                               │  audit log (Postgres + JSONL)
                                               └► DuckDB (in-process) ─► /data/lake/*.parquet
 postgres :5432 (roles, users, policies, audit)
```

| Layer | Choice | Reason |
|---|---|---|
| API | Django 6 + DRF | schema, API contracts, Django admin as super-admin UI |
| Auth | SimpleJWT, RS256, rotating refresh + blacklist | asymmetric signature → tamper demo |
| Query | DuckDB over Parquet | live wrangling without an ETL step |
| Deps | Poetry | as specified |
| UI | React 18 + Vite + TS + Tailwind + TanStack Query + Recharts | matches inspiration conventions |
| Design | Red Hat design language (Red Hat Display/Text/Mono, #EE0000 on #151515, 3px radii, PatternFly-style chips) | as specified — style only, no Red Hat branding |
| Runtime | Docker Compose: `db`, `backend`, `frontend` | reproducible lab |

## Data lake — 14 Parquet datasets (fictional city "Mji Mpya", 12 districts)

| Domain | Dataset | Key PII |
|---|---|---|
| Living locales | `citizens`, `residences` | national_id, ssn, names, phone, email, address, geo |
| Medical care | `medical_records` | diagnosis, allergies |
| Public transit | `transit_trips` | card_id, board/alight times |
| Private vehicles | `vehicle_tracking` | plate, GPS pings |
| Felonies | `felonies` | offence, sentence |
| Criminal infractions | `infractions` | fines |
| Sociological | `relationships` | citizen ↔ citizen edges |
| Amenities | `amenities` | — (swimming pools, gyms, clinics…) |
| Weather & microclimate | `weather` | — |
| Infrastructure health | `infrastructure` | — |
| Citizen feedback | `feedback` | author id, district, channel |
| Disaster & hazard | `hazard_alerts` | — |
| E-government | `egov_logs` | ip address, device |

Generated deterministically (seeded) by `manage.py generate_lake` on first boot.

## Permission grid

`Role × Dataset → Policy`:

- `mode`: `deny` | `aggregate` | `row`
- `column_rules`: `{column: clear | mask | pseudonym | fake | generalize | redact}`;
  unlisted columns default to `redact` (deny-by-default)
- `group_by` / `metrics`: dimensions and measures allowed in aggregate mode
- `min_group_size`: k-anonymity floor — smaller groups are suppressed
- `cross_analyze`: dataset is visible to the SQL workbench for joins
- `max_rows`

Plus per-role **API capabilities** (`lake.browse`, `lake.aggregate`, `lake.sql`,
`audit.view_own`, `audit.view_all`, `grid.view_all`).

Transforms are compiled into a DuckDB view per (role, dataset). Filters run on
the *transformed* view, so a masked column cannot be used as an oracle.
Pseudonyms are `sha256(secret ‖ role ‖ value)` — stable within a role (joins
still work) but unlinkable across roles.

| Role | Highlights |
|---|---|
| Medical personnel | identity + residence + medical; no crime, vehicle, transit, amenities |
| Rapid response | identity + residence + hazards/weather/infra; no medical detail, no crime |
| Law enforcement | identity, felonies, infractions, vehicles; transit aggregate only |
| Civil engineer | infrastructure/amenities rows; people, climate, housing as k-anonymous aggregates |
| Sociologist | relationships + citizens with fake names and pseudonymous IDs |
| Policy maker | de-identified feedback (no author, district, channel); aggregates elsewhere |
| Transport official | trips + thin citizen slice (name, sex, age band, disability) |
| Climatologist | weather + hazards rows; everything else aggregate |
| Administrator | every dataset, lightly obfuscated; full audit + SIEM view; cannot edit grid |
| Super-admin | Django superuser — edits grid in Django admin only |

## API

```
POST /api/auth/token/            POST /api/auth/token/refresh/
POST /api/auth/token/verify/     POST /api/auth/logout/
GET  /api/auth/me/               GET  /api/auth/jwks/   GET /api/auth/demo-accounts/
GET  /api/grid/                  GET  /api/grid/my-policy/
GET  /api/lake/datasets/         GET  /api/lake/datasets/{slug}/
POST /api/lake/datasets/{slug}/query/      POST /api/lake/datasets/{slug}/aggregate/
GET  /api/lake/sql/tables/       POST /api/lake/sql/
GET  /api/audit/logs/            GET  /api/audit/stats/   GET /api/audit/detections/
GET  /api/audit/export/  (NDJSON for SIEM)        GET /api/health/
```

## Audit / SIEM

Middleware records every `/api/` call: user, role, path, method, status,
outcome (`allowed`/`denied`/`unauthenticated`/`throttled`/`error`), dataset,
columns + transforms applied, rows returned, SQL text, IP, UA, duration, token
`jti`. Login attempts record the attempted username (never the password).
Written to Postgres and to `logs/audit.jsonl`. Detection rules: brute force
(failed logins per user/IP), token tampering (invalid signatures), privilege
probing (bursts of 403s from one account). Login is throttled.

## Frontend pages

Login (role picker) · Overview · Data Lake (catalog → explorer with Schema /
Records / Aggregate tabs) · SQL Workbench · Permission Grid · Token Lab (decode,
countdown, refresh, verify, tamper & replay, alg=none attack, public key) ·
Audit & SIEM.

## Execution order

1. Repo skeleton, plan, README
2. Backend: settings, accounts (User+Role), grid models, catalog + generator,
   policy engine, lake API, audit middleware + API, seeding commands, admin
3. Backend tests (policy engine, auth, tamper rejection, audit)
4. Frontend: design tokens, shell, pages
5. Dockerfiles, compose, entrypoint (key generation, migrate, seed, generate)
6. `docker compose up --build`, smoke-test every role end to end
