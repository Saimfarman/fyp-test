# LeadPitch

LeadPitch helps digital-service sellers discover local businesses in Pakistan
that lack a website or need practical website, SEO, and marketing improvements.
It combines responsible local-business discovery, explainable website audits,
bilingual outreach, proposal generation, and editable website prototypes.

## What is included

- Responsive Next.js frontend and installable PWA shell.
- Quart API with session authentication, workspaces, roles, credits, leads,
  audits, pitches, proposals, prototypes, reports, API keys, and webhooks.
- PostgreSQL persistence with ordered SQL migrations.
- Redis-backed queue and background worker.
- OpenStreetMap, Overpass, and Nominatim discovery integrations.
- SSRF-aware website audits with scoring and persisted issues.
- Deterministic English and Urdu pitch and proposal generation.
- Sanitized HTML generation and HTML/React project ZIP exports.

Read the detailed design documents in this order:

1. [Product scope](docs/product-scope.md)
2. [Architecture](docs/architecture.md)
3. [API overview](docs/api-overview.md)
4. [Production deployment](docs/deployment.md)

## Requirements

### Docker setup (recommended)

- Git
- Docker Desktop with the Linux engine running
- At least 4 GB of memory available to Docker
- Internet access on the first run to download base images and packages

The Docker setup runs PostgreSQL, Redis, the backend API, the worker, and the
frontend. Node.js and Python do not need to be installed on the host for this
option.

### Local development without Docker

- Python 3.12 or newer
- Node.js 22 or newer and npm
- PostgreSQL 16 or a compatible PostgreSQL server
- Redis 7 or a compatible Redis server

Docker is still the simplest way to provide the PostgreSQL and Redis
dependencies.

## Run after cloning

Clone the repository and enter its directory:

```powershell
git clone https://github.com/Saimfarman/fyp-test.git
cd fyp-test
```

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and set a `SECRET_KEY` containing at least 32 characters. The
development defaults are suitable for a local Docker run. Do not commit `.env`
or put production secrets in GitHub.

Make sure Docker Desktop is open and its **Linux containers/engine** is
running. Then build and start the complete stack:

```powershell
docker compose up --build
```

Run it in the background instead:

```powershell
docker compose up --build -d
```

Open the application at <http://localhost:3000>. The backend API is available
at <http://localhost:8000>.

The backend applies all ordered migrations from `backend/migrations/` before
starting. The current migration set includes the initial schema, leads,
audits, pitches, prototypes, platform features, and completion changes.

### Useful Docker commands

```powershell
# Show running services
docker compose ps

# Follow application logs
docker compose logs -f backend worker frontend

# Follow one service
docker compose logs -f backend

# Stop containers but keep database and Redis data
docker compose down

# Stop containers and remove persistent local data (destructive)
docker compose down -v

# Rebuild one service
docker compose build backend
docker compose up -d backend

# Start the stack again after it has been stopped
docker compose start
```

The named `postgres_data` and `redis_data` volumes preserve local data when
`docker compose down` is used. Use `down -v` only when you intentionally want
to reset the local database and Redis state.

## Environment variables

The supported variables are documented in `.env.example`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Application environment. |
| `SECRET_KEY` | placeholder | Session and signing secret; use 32+ random characters. |
| `DATABASE_URL` | Compose PostgreSQL URL | Async PostgreSQL connection URL. |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL used by the API and worker. |
| `SESSION_COOKIE_SECURE` | `false` | Set to `true` only when using HTTPS. |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | Browser origin allowed by the API. |
| `API_PORT` | `8000` | Host port mapped to the backend container. |
| `FRONTEND_PORT` | `3000` | Host port mapped to the frontend container. |

When running the Compose stack, use service names such as `postgres` and
`redis` in connection URLs. When running the backend directly on the host, use
`localhost` instead.

## Production-style Docker run

Review [docs/deployment.md](docs/deployment.md), replace all development
secrets and credentials, configure a TLS reverse proxy, and set the public
frontend origin. Start the production overlay with:

```powershell
docker compose -f compose.yml -f compose.prod.yml up --build -d
```

For production, set `SESSION_COOKIE_SECURE=true` and use a strong unique
`SECRET_KEY`. Do not expose PostgreSQL or Redis directly to the public
internet. Back up the PostgreSQL volume before schema upgrades.

The health endpoints are:

- Liveness: `GET /health/live`
- Readiness: `GET /health/ready`

## Run locally without building containers

### Backend

Create and activate a virtual environment from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

Start PostgreSQL and Redis separately. The backend reads environment variables
from the process environment; it does not load `.env` automatically when run
outside Compose. Set the local connection values in the PowerShell session:

```powershell
$env:APP_ENV = "development"
$env:SECRET_KEY = "replace-with-a-long-random-secret-of-32-characters"
$env:DATABASE_URL = "postgresql+asyncpg://leadpitch:leadpitch@localhost:5432/leadpitch"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:SESSION_COOKIE_SECURE = "false"
$env:FRONTEND_ORIGIN = "http://localhost:3000"

cd backend
python -m app.migrate
hypercorn "app:create_app()" --bind 0.0.0.0:8000
```

In a second terminal, start the worker:

```powershell
cd backend
..\.venv\Scripts\Activate.ps1
python -m app.worker
```

### Frontend

In a separate terminal:

```powershell
cd frontend
npm ci
npm run dev
```

The development frontend runs at <http://localhost:3000>. For a production
frontend build:

```powershell
npm run build
npm start
```

## Testing and code quality

Run backend tests from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
```

Run backend linting:

```powershell
.\.venv\Scripts\python.exe -m ruff check backend
```

Run frontend linting and the production build:

```powershell
cd frontend
npm ci
npm run lint
npm run build
```

The same backend compile/lint and frontend build checks run in
[`.github/workflows/ci.yml`](.github/workflows/ci.yml) on pushes and pull
requests.

## Troubleshooting

### Docker cannot connect to `dockerDesktopLinuxEngine`

An error such as:

```text
failed to connect to the docker API ... dockerDesktopLinuxEngine
```

means the Docker CLI is installed but Docker Desktop's Linux daemon is not
running. Start Docker Desktop, wait until it reports that Docker is running,
then verify the daemon:

```powershell
docker version
docker info
```

The command must show both client and server information. If Docker is using
the wrong context, list and select the Desktop Linux context:

```powershell
docker context ls
docker context use desktop-linux
```

Then retry:

```powershell
docker compose up --build
```

### Port already in use

Change `API_PORT` or `FRONTEND_PORT` in `.env`, then recreate the services:

```powershell
docker compose up --build -d
```

### Check service readiness

```powershell
docker compose ps
Invoke-WebRequest http://localhost:8000/health/live
Invoke-WebRequest http://localhost:8000/health/ready
```

If readiness is unavailable, inspect the backend, PostgreSQL, and Redis logs:

```powershell
docker compose logs backend postgres redis
```

## Responsible use

LeadPitch must use official and public data sources, respect OSM attribution
and provider usage policies, obey `robots.txt` and crawl limits, avoid
automated spam, and provide a business opt-out/removal process. Public pitch
links must not expose private workspace notes or contact history.
