# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

ai-remediation-integration

## Roadmap

### fastapi-backend-structure — Create FastAPI backend with proper modular structure

Status: done

Acceptance:
- backend/app/main.py exports FastAPI app with create_app factory
- backend/app/api/ with scan, findings, health endpoints
- backend/app/services/ with scanner service wrapping existing CLI logic
- backend/app/models/ with Pydantic models for findings, scans
- backend/app/core/ with config, auth, database setup
- SQLite persistent storage for scans and findings
- backend/tests/ with meaningful pytest tests

Implementation: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/core/security.py`, `backend/app/models/domain.py`, `backend/app/models/schemas.py`, `backend/app/services/scanner.py`, `backend/app/api/deps.py`, `backend/app/api/routes/health.py`, `backend/app/api/routes/scans.py`, `backend/app/api/routes/findings.py`, `backend/app/api/__init__.py`

Tests: `backend/tests/conftest.py`, `backend/tests/test_models.py`, `backend/tests/test_scanner.py`, `backend/tests/test_api_scans.py`, `backend/tests/test_api_findings.py`

### react-frontend-skeleton — Create React + TypeScript + Vite frontend skeleton

Status: done

Acceptance:
- frontend/package.json with build, test scripts
- frontend/src with components, API client
- Dashboard showing scan results
- Scan trigger form
- Findings list with severity filtering

Implementation: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/index.css`, `frontend/src/types/index.ts`, `frontend/src/api/client.ts`, `frontend/src/hooks/useAuth.ts`, `frontend/src/components/Layout.tsx`, `frontend/src/pages/Login.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/Scans.tsx`, `frontend/src/pages/Findings.tsx`, `frontend/Dockerfile`, `frontend/nginx.conf`

Tests: `frontend/src/test/Login.test.tsx`, `frontend/vitest.config.ts`, `frontend/src/test/setup.ts`

### auth-oidc-keycloak — Implement OIDC authentication with Keycloak

Status: done

Acceptance:
- Keycloak in docker-compose
- Authorization code flow with PKCE
- Role-based access (viewer, operator, admin)
- Protected API endpoints
- Login/logout flows

Implementation: `docker-compose.yml`, `keycloak/realm.json`, `backend/app/core/security.py`, `backend/app/api/deps.py`, `frontend/src/hooks/useAuth.ts`, `frontend/src/pages/Login.tsx`

Tests: `backend/tests/test_api_scans.py`, `backend/tests/test_api_findings.py`, `frontend/src/test/Login.test.tsx`

### ci-cd-pipeline — Add GitHub Actions CI pipeline

Status: done

Acceptance:
- .github/workflows/ci.yml tests backend and frontend
- Builds both Dockerfiles
- At least 12 backend tests, 3 frontend tests

Implementation: `.github/workflows/ci.yml`, `backend/Dockerfile`, `frontend/Dockerfile`

Tests: `backend/tests/`, `frontend/src/test/`

### portfolio-docs — Add required portfolio documentation

Status: done

Acceptance:
- portfolio.json at root
- CHANGELOG.md
- pyproject.toml with author metadata
- Updated README with accurate architecture
- docs/ if useful

Implementation: `portfolio.json`, `CHANGELOG.md`, `pyproject.toml`, `README.md`, `compose.yaml`, `.env.example`, `LICENSE`, `CONTRIBUTING.md`

### ai-remediation-integration — Integrate AI-powered remediation analysis for findings

Status: done

Acceptance:
- LLM service with multi-provider support (OpenAI, Anthropic, Gemini, Ollama)
- API endpoint to generate AI remediation for a finding
- AI analysis stored in finding.ai_analysis field
- Frontend displays AI remediation in findings detail
- Proper error handling for missing/invalid LLM credentials

Implementation: `backend/app/services/llm.py`, `backend/app/api/routes/ai.py`, `backend/app/api/__init__.py`, `backend/app/models/schemas.py`, `frontend/src/api/client.ts`, `frontend/src/pages/Findings.tsx`, `backend/tests/test_ai.py`

Tests: `backend/tests/test_ai.py`

