# Mji Mpya — Smart City Big Data Access Lab

A containerised lab for **role-based, column-aware access control over a big-data lake**.

Fourteen synthetic Parquet datasets from the fictional smart city of *Mji Mpya* (medical care,
public transit, private vehicle tracking, felonies, infractions, social relationships, residences,
amenities, weather, infrastructure health, citizen feedback, hazard alerts and e-government logs)
are queried live with **DuckDB**. A **permission grid** decides, for each of nine roles and each
dataset, whether the caller is denied, gets k-anonymous aggregates only, or gets record-level rows
in which every column is shown, masked, pseudonymised, faked, generalised or removed.
Authentication uses **RS256-signed JWTs**, and every request is written to an **audit log** that a
SIEM can ingest.

> Django + DRF · SimpleJWT · DuckDB · PyArrow · Poetry · PostgreSQL · React + Vite + Tailwind · Docker Compose

## Run it

```bash
docker compose -f docker/docker-compose.yml up --build -d
```

| What | Where |
|---|---|
| Lab UI | http://localhost:8080 |
| Super-admin console (Django admin) | http://localhost:8080/admin/ — `superadmin` / `SuperAdmin@4030` |
| API health | http://localhost:8080/api/health/ |

First boot migrates the database, seeds roles, the grid and demo users, generates the RSA key
pair and builds the data lake (about 150k rows, seeded so every run is identical).

Every role has a demo account with password **`SmartCity@4030`**:

| Role | Username | Sees |
|---|---|---|
| Medical Personnel | `medic` | identity, home address, full medical history — no crime, vehicles, transit or amenities |
| Rapid Response | `responder` | who lives where, gate codes, mobility needs, blood type & allergies, hazards, road state |
| Law Enforcement Official | `officer` | identities, felonies, infractions, vehicle pings — medical denied, transit aggregate only |
| Civil Engineering Contractor | `engineer` | infrastructure rows; people, housing and climate as k ≥ 10 aggregates; no SQL |
| Sociologist | `sociologist` | social graph + citizens with fake names and keyed-hash IDs that still join |
| Policy Maker | `policymaker` | feedback with author, district, channel and upvotes removed; aggregates elsewhere |
| Transport Official | `transport` | every board/alight event + name, age band and disability of the rider |
| Climatologist | `climatologist` | raw sensor readings and hazards; everything else aggregate |
| Administrator | `admin` | every silo through a pseudonymised lens, plus the whole audit trail and SIEM view |

The **super-admin** is a Django superuser with no role: it edits the grid in the Django console but
cannot obtain an API token or read the lake. The **administrator** role reads the lake through an
obfuscated lens and cannot edit the grid or any record.

## Things to try

1. **Same table, nine views.** Open *Data Lake → Citizen Registry* as `medic`, then as `sociologist`,
   `transport` and `engineer`. Compare the *Schema & column rules* tab.
2. **Ask for what you may not have.** As `medic`, open *Felony Cases* and press *Send the request
   anyway*, or run `SELECT * FROM felonies` in the SQL Workbench. You get a 403 with the reason.
3. **Forge a token.** In the *Token Lab*, click *Escalate to administrator*, then *Send forged token*.
   The RS256 signature no longer matches → 401. Try `alg: none` too.
4. **Escape the sandbox.** In the workbench, `SELECT * FROM read_parquet('/data/lake/citizens.parquet')`
   is refused: the role's policy views are the only tables that exist.
5. **Trip the SIEM.** Fail a login five times, forge a token, or probe five denied datasets. Then sign
   in as `admin` and open *Audit & SIEM* — detections are mapped to MITRE ATT&CK.
6. **Change the grid.** Sign in to `/admin/` as `superadmin`, edit a policy (e.g. give `medical`
   aggregate access to `amenities`), and refresh the lab.

## How it works

```
browser ─► frontend (nginx :8080) ─/api, /admin─► backend (gunicorn :8000)
                                                    │ DRF + SimpleJWT (RS256, role-bound)
                                                    │ permission grid ─► policy engine ─► DuckDB ─► Parquet
                                                    └ audit middleware ─► Postgres + audit.jsonl
```

- **Policy engine** (`backend/apps/lake/engine.py`) compiles a grid cell into a DuckDB `SELECT`
  that rewrites each column according to its rule and its *kind* (an email keeps its domain, a phone
  its last four digits, a date of birth becomes an age band…). Unlisted columns are dropped: deny by
  default. Filters and sorts run on the transformed view, so a masked column cannot be used as an oracle.
- **Pseudonyms** are `sha256(secret ‖ role ‖ value)`: stable within one role, so joins still work,
  but unlinkable across roles.
- **Aggregates** only use dimensions and measures declared in the catalog and allowed by the policy;
  groups smaller than the policy's `min_group_size` are suppressed and counted.
- **SQL workbench** materialises only the caller's policy views in an in-memory DuckDB, then disables
  external access, extension loading and configuration changes before running a single `SELECT`
  under a timeout.
- **JWTs** are signed with a 2048-bit RSA private key kept on a Docker volume; the public key is
  published at `/api/auth/jwks/`. Tokens carry the role, and are rejected if the account's role has
  since changed. Refresh tokens rotate and are blacklisted after use or logout. Login is throttled.
  Tokens live in `localStorage` *for illustration only* — production would use HttpOnly cookies.
- **Audit** records method, path, status, outcome, user, role, dataset, columns, rows returned,
  SQL text, IP, user agent, duration and token `jti` for every `/api/` call — never passwords.
  `GET /api/audit/export/` streams ECS-style NDJSON for Wazuh, Elastic or Splunk.

## Repository layout

```
backend/
  apps/accounts   roles, users, role-bound JWT auth, auth endpoints, seed_lab command
  apps/grid       Dataset + Policy models, default grid (seed.py), grid API
  apps/lake       catalog, deterministic generator, policy engine, lake API
  apps/audit      audit model, middleware, SIEM detections, audit API
  tests/          pytest suite (auth, tampering, policies, sandbox, detections)
frontend/         React + Vite + Tailwind, Red Hat design language
docker/           docker-compose.yml, .env.example
docs/PLAN.md      design plan
```

## Development

```bash
# Backend tests (inside the dev image; local Python may be too new for the wheels)
docker build --target development -t smartcity-backend:dev backend
docker run --rm smartcity-backend:dev pytest

# Frontend with hot reload against a running backend on :8000
cd frontend && pnpm install && pnpm dev     # http://localhost:5173

# Rebuild the lake at a different size
docker compose -f docker/docker-compose.yml exec backend python manage.py generate_lake --force --scale 3

# Restore the default grid after experimenting in the admin
docker compose -f docker/docker-compose.yml exec backend python manage.py seed_lab --reset-grid
```

All people, places and records are synthetic.
