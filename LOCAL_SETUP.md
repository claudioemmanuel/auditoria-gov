# OpenWatch Local Development Setup — Complete

## Status: ✅ Backend Services Running

### Currently Active Services

```
✅ API (FastAPI)              http://localhost:8000
   - API Documentation       http://localhost:8000/docs
   - Health check            http://localhost:8000/health

✅ Database (PostgreSQL 17)   localhost:5432
✅ Cache (Redis 7)            localhost:6379
✅ Worker (Celery)            Running background jobs
```

---

## Frontend Setup (Next.js)

### Step 1: Install Node.js

**Windows:**

1. Download and install from <https://nodejs.org/> (LTS 20.x or later)
2. Verify: Open new terminal and run:

   ```powershell
   node --version  # Should show v20.x or later
   npm --version   # Should show npm version
   ```

**macOS:**

```bash
brew install node@20
```

**Linux:**

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### Step 2: Install Frontend Dependencies

```bash
cd web
npm ci              # Clean install (uses package-lock.json)
```

### Step 3: Start Frontend Dev Server

```bash
# From the web/ directory
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

The frontend will be available at: **<http://localhost:3000>**

---

## Backend Setup

### Current Status

```
Service           Status       URL/Port
─────────────────────────────────────────
API               ✅ Running   http://localhost:8000
PostgreSQL        ✅ Running   localhost:5432
Redis             ✅ Running   localhost:6379
Celery Worker     ✅ Running   Background jobs
Alembic           ✅ Complete  All migrations applied
```

### Database Migrations

Migrations run automatically on container startup. To verify:

```bash
# View migration history
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml \
  exec api alembic -c api/alembic.ini history

# View migrating to latest
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml \
  exec api alembic -c api/alembic.ini upgrade head
```

---

## Backend Testing

### Prerequisites

```bash
# Install Python 3.12+ (ensure uv is available)
uv --version    # Should show version
pip list        # Python packages
```

### Run Tests

```bash
# From project root
uv sync --extra test              # Install test dependencies
uv run --extra test pytest -q     # Run all tests (quick mode)

# With coverage report
uv run --extra test pytest --cov=shared --cov-fail-under=100 --cov-report=html

# Single test file
uv run --extra test pytest tests/typologies/test_t03.py -v

# Watch mode (requires pytest-watch)
uv run --extra test ptw
```

### Type Checking

```bash
mypy .              # Type check all Python files
mypy shared/        # Type check specific module
mypy --strict .     # Strict mode
```

### Code Quality

```bash
# Formatting
black .             # Auto-format code
isort .             # Organize imports

# Linting
ruff check .        # Fast linting
pylint shared/      # Deep analysis

# Security
bandit -r .         # Find security issues
safety check        # Check dependencies
```

---

## Frontend Testing

### Run Quality Checks

```bash
cd web

# Linting
npm run lint        # ESLint (code quality)

# Type checking
npx tsc --noEmit    # TypeScript without building

# Build verification
npm run build       # Full Next.js build

# All checks together
npm run lint && npx tsc --noEmit && npm run build
```

### Browser Testing

```bash
cd web
npm run dev                 # Start dev server
# Navigate to http://localhost:3000 in browser
# Open Developer Tools (F12) to check console for errors
```

---

## Manage Docker Services

### View Logs

```bash
# All services
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml logs -f

# Specific service
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml logs -f api
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml logs -f postgres
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml logs -f redis
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml logs -f worker-primary

# Last 50 lines
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml logs --tail=50
```

### Stop Services

```bash
# Stop all (keep data)
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml stop

# Stop and remove containers (keep volumes/data)
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml down

# Stop and remove everything including data
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml down -v
```

### Restart Services

```bash
# Restart all
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml restart

# Restart specific service
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml restart api
```

### Execute Commands in Containers

```bash
# PostgreSQL shell
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml \
  exec postgres psql -U auditoria -d auditoria

# Redis CLI
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml \
  exec redis redis-cli

# API shell
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml \
  exec api bash
```

---

## API Endpoints (Testing)

### Health Check

```bash
curl http://localhost:8000/health
```

### API Documentation

Visit: **<http://localhost:8000/docs>** (Swagger UI)

The interactive Swagger interface allows testing all public endpoints.

---

## Common Development Workflows

### 1. Making Changes to Backend

```bash
# Make code changes in shared/ or api/
# Tests run automatically or manually:
uv run --extra test pytest -q

# Check types
mypy . --strict

# If you added new migrations:
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml \
  exec api alembic -c api/alembic.ini upgrade head
```

### 2. Making Changes to Frontend

```bash
cd web

# Make changes to src/

# Type check in real time
npx tsc --noEmit --watch

# Linter check
npm run lint

# Access dev server at http://localhost:3000
# HMR (Hot Module Reload) auto-updates browser on save
```

### 3. Database Schema Changes

```bash
# Create migration
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml \
  exec api alembic -c api/alembic.ini revision --autogenerate \
  -m "describe your change"

# Review generated migration in api/alembic/versions/

# Apply migration
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml \
  exec api alembic -c api/alembic.ini upgrade head

# Test the change
uv run --extra test pytest -q
```

---

## Troubleshooting

### Frontend shows "API connection refused"

**Problem**: Frontend can't reach API at localhost:8000
**Solution**:

```bash
# Verify API is running
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml ps

# Check API logs
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml logs api

# Restart services
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml restart api
```

### PostgreSQL connection error

**Problem**: "Connection refused on port 5432"
**Solution**:

```bash
# Verify PostgreSQL container is running
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml ps postgres

# Check health
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml exec postgres \
  pg_isready -U auditoria

# View logs
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml logs postgres
```

### Tests failing with "database locked"

**Problem**: SQLite tests conflict (unlikely with PostgreSQL) or migrations incomplete
**Solution**:

```bash
# Verify migrations are up to date
uv sync --extra test
uv run --extra test pytest --migrate-db -q

# Reset test database
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml down -v
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml up -d postgres
# Wait for PostgreSQL to be healthy, then retry tests
```

### Docker Desktop not starting

**Problem**: "Docker daemon not running"
**Solution**:

1. Open Docker Desktop application
2. Wait for it to start (usually shows in system tray)
3. Retry docker commands

---

## Using Make (Simplified Commands)

If you have `make` installed (Windows: use `choco install make` or WSL):

```bash
make dev                    # Start lightweight dev (API + DB, no containers for web)
make dev-full              # Start full stack with all containers
make dev-down              # Stop all services
make logs                  # View logs from all services

# Backend tests
make test                  # Run pytest -q

# Frontend checks
make lint-web              # npm run lint + npm run build in web/
```

---

## Full Development Stack (Optional)

If you want all services containerized (takes more RAM ~7.5 GB):

```bash
docker compose up -d       # Starts frontend, backend, database, redis, worker
```

Access:

- Frontend: <http://localhost:3000>
- API: <http://localhost:8000>
- API Docs: <http://localhost:8000/docs>

---

## Next Steps

1. ✅ **Backend is ready** — API running at <http://localhost:8000>
2. 📦 **Install Node.js** if not already installed
3. 🚀 **Start frontend** — `cd web && npm ci && npm run dev`
4. 🌐 **Access** <http://localhost:3000>
5. 📝 **Make changes** and see HMR (hot reload) in action
6. ✅ **Run tests** as you develop

---

## Documentation

- **Architecture**: [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- **API Reference**: <http://localhost:8000/docs> (Swagger UI)
- **Contributing Guide**: [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Coding Rules**: [.claude/rules/coding.md](../.claude/rules/coding.md)
- **Testing Rules**: [.claude/rules/testing.md](../.claude/rules/testing.md)

---

## Getting Help

**Check logs:**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml logs -f
```

**Check service status:**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml ps
```

**Run health check:**

```bash
curl http://localhost:8000/health
```

**Review CLAUDE.md for conventions:**

```bash
cat CLAUDE.md
```
