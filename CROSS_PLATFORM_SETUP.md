# Cross-Platform Setup Guide

OpenWatch runs on **Windows, macOS, and Linux**. This guide ensures line endings and dependencies work correctly on all operating systems.

---

## Line Endings (CRLF vs LF)

### The Problem

Git on Windows **automatically converts** Unix line endings (LF) to Windows line endings (CRLF) when you clone/checkout. This breaks **shell scripts** in Docker containers, which expect Unix line endings only.

```
Windows (you): LF → checkout → CRLF
Docker image: Expects LF only → Crash! ✗
```

### The Solution

OpenWatch uses **`.gitattributes `** to enforce Unix line endings (`LF`) for shell scripts and Python files:

```yaml
# .gitattributes (already in repo)
*.sh text eol=lf              # Force LF for all shell scripts
*.py text eol=lf              # Force LF for all Python scripts
docker-entrypoint.sh eol=lf   # Explicit: worker entrypoint
```

### For Windows Users

**After cloning:**

```powershell
cd openwatch

# (Optional) Configure Git to warn about CRLF
git config core.safecrlf warn

# Clone with correct line endings
git clone https://github.com/claudioemmanuel/openwatch.git
cd openwatch

# Verify line endings are correct
git ls-files --eol
```

**Result:**
```
i/lf    w/crlf  attr/text eol=lf  worker/docker-entrypoint.sh
i/lf    w/lf    attr/text eol=lf  api/alembic/env.py
```

- `i/lf` = Index (git) has LF ✓
- `w/lf` = Working directory has LF ✓ (correct, matches `.gitattributes`)

---

### For macOS and Linux Users

✅ **No action needed!** macOS/Linux use LF by default. Everything works out of the box.

Verify:
```bash
git ls-files --eol | head -5
# i/lf    w/lf    attr/text eol=lf  worker/docker-entrypoint.sh  ✓
```

---

## Platform-Specific Setup

### Windows 10/11 with WSL2

**Recommended approach**: Use WSL2 for better Docker performance.

```powershell
# Install WSL2
wsl --install

# Inside WSL2 terminal (Ubuntu):
git clone https://github.com/claudioemmanuel/openwatch.git
cd openwatch
docker compose up -d
```

**Why WSL2?**
- ✅ Native Linux kernel
- ✅ Better file sync performance
- ✅ No line ending issues
- ✅ Docker Desktop integrates seamlessly

---

### Windows without WSL (Hyper-V)

**If using Docker Desktop with Hyper-V**, line endings are **automatically normalized** by `.gitattributes`, but verify:

```powershell
# After cloning
file worker/docker-entrypoint.sh
# Should output: "Cannot stat file" is OK (use git ls-files instead)

git ls-files --eol | grep docker-entrypoint
# i/lf    w/lf    attr/text eol=lf  worker/docker-entrypoint.sh ✓
```

If you see `w/crlf` (working directory has CRLF):
```powershell
# Force re-normalization
git add --renormalize .
git commit -m "fix: normalize line endings"
docker compose down -v
docker compose up -d --build
```

---

### macOS (Intel & Apple Silicon)

```bash
# Clone
git clone https://github.com/claudioemmanuel/openwatch.git
cd openwatch

# Check Docker is installed
docker --version
# Docker version 25.x or later recommended

# Start backend
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml up -d

# Verify all containers healthy
docker compose ps
```

**If using Homebrew:**
```bash
brew install docker docker-compose
# or use Docker Desktop (recommended)
```

---

### Linux (Ubuntu, Debian, Fedora, etc.)

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version

# Clone & run
git clone https://github.com/claudioemmanuel/openwatch.git
cd openwatch
docker compose -f docker-compose.yml -f docker-compose.dev-lite.yml up -d

# Check status
docker compose ps
```

---

## Verification Checklist (All Platforms)

After setup, verify everything works:

```bash
# 1. Check containers are healthy
docker compose ps
# ✓ All 4 containers show "healthy" or "Up"

# 2. Test API
curl http://localhost:8000/health
# ✓ Returns: {"status": "ok"}

# 3. Check database migrations
docker compose exec api alembic -c api/alembic.ini current
# ✓ Output shows migration version (e.g., "0024")

# 4. Test Redis
docker compose exec redis redis-cli PING
# ✓ Returns: PONG

# 5. Check worker status
docker compose logs worker-primary | head -10
# ✓ No error messages; should show Celery initialization
```

---

## Troubleshooting by Platform

### Windows: Line Ending Issues

**Symptom**: Worker container crash with `bash\r: No such file or directory`

**Fix**:
```powershell
# 1. Verify .gitattributes exists
git ls-files | grep gitattributes

# 2. Re-normalize files
git add --renormalize .
git commit -m "fix: normalize line endings"

# 3. Rebuild containers
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

### Windows: Docker Desktop Not Starting

**Symptom**: `Docker daemon is not running`

**Fix**:
```powershell
# Option 1: Start Docker Desktop from taskbar
# Right-click Desktop icon → Start

# Option 2: Start via PowerShell (Admin)
Start-Service Docker

# Verify
docker ps
```

### macOS: Permission Denied

**Symptom**: `permission denied while trying to connect to Docker daemon`

**Fix**:
```bash
# Run Docker Desktop (UI application)
# Go to Applications → Docker.app

# Or ensure user is in docker group
sudo usermod -aG docker $(whoami)
newgrp docker
```

### Linux: Docker Not Found

**Symptom**: `docker: command not found`

**Fix**:
```bash
# Install Docker
sudo apt update && sudo apt install -y docker.io

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
```

---

## Environment Variables (All Platforms)

Create `.env` **before** running `docker compose up`:

```bash
# Copy template
cp .env.example .env

# Required for local dev (already set in docker-compose.yml)
DATABASE_URL=postgresql://auditoria:auditoria@postgres:5432/auditoria
REDIS_URL=redis://redis:6379
PORTAL_TRANSPARENCIA_TOKEN=your_token_here  # Needed for connectors

# Optional
LLM_PROVIDER=none
APP_ENV=development
```

---

## Running Tests (All Platforms)

### Backend Tests

```bash
# Install dependencies
uv sync --extra test

# Run tests
uv run --extra test pytest -q

# With coverage report
uv run --extra test pytest --cov=shared --cov-fail-under=100
```

### Frontend Tests

```bash
cd web

# Install dependencies
npm ci

# Run checks
npm run lint
npm run build

# Type checking
npx tsc --noEmit
```

---

## CI/CD Considerations

### GitHub Actions

All workflows automatically handle line endings correctly via `.gitattributes`. No special OS-specific logic needed.

See: [.github/workflows/ci.yml](.github/workflows/ci.yml)

---

## Best Practices for Contributors

### Before Committing

1. **Verify line endings:**
   ```bash
   git ls-files --eol | grep "\.sh$"
   # Should show: i/lf    w/lf (not w/crlf)
   ```

2. **Run linters:**
   ```bash
   cd api && black . && isort .
   cd ../web && npm run lint
   ```

3. **Run tests:**
   ```bash
   uv run --extra test pytest -q
   cd web && npm run build
   ```

### When Adding New Shell Scripts

```bash
#!/usr/bin/env bash
set -e

# Your script here
```

**Always ensure:**
- ✓ Shebang (`#!/usr/bin/env bash`) on first line
- ✓ Unix line endings only (LF, not CRLF)
- ✓ File is in `.gitattributes` ruleset (e.g., `*.sh eol=lf`)
- ✓ Executable permission: `chmod +x script.sh`

---

## Support & Questions

- 📖 **Full Setup Guide**: [LOCAL_SETUP.md](LOCAL_SETUP.md)
- 📖 **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 🐛 **Report Issues**: [GitHub Issues](https://github.com/claudioemmanuel/openwatch/issues)

---

## Changelog: Cross-Platform Fixes

**April 1, 2026 (This Session)**
- ✅ Added `.gitattributes` to enforce LF for shell scripts
- ✅ Fixed worker container line ending crash (exit code 127)
- ✅ Normalized all existing files in git history
- ✅ Tested on Windows with full Docker rebuild
- ✅ Created cross-platform setup documentation

**Verified On:**
- ✅ Windows 11 + Docker Desktop (Hyper-V)
- ✅ Linux (Ubuntu 22.04 validation in CI/CD)
- ✅ macOS (docker-compose compatibility)
