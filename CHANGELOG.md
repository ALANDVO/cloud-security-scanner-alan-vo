# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-10-21

### Added
- AI-powered executive summary for security scans
- API endpoint to generate executive summary (POST /api/ai/executive-summary)
- Executive summary includes risk rating, key findings summary, top 3 priority actions, compliance gaps, and strategic recommendations
- Summary stored persistently in scan.ai_summary field
- Frontend integration with expandable executive summary panel in Scans page
- AI provider status indicator with configuration guidance in Scans page
- 6 new backend tests for executive summary service and API routes

### Changed
- Updated Scan model with ai_summary field
- Extended backend schemas with AIExecutiveSummaryRequest, AIExecutiveSummaryResponse models
- Extended frontend API client and types with executive summary methods
- Enhanced Scans page with executive summary generation button, loading states, and markdown rendering
- LLM service now supports executive summary generation with fallback mode

## [1.1.0] - 2026-10-14
## [1.0.1] - 2026-10-14
## [1.0.0] - 2026-10-13

### Added
- FastAPI backend with modular structure (core, models, services, api)
- SQLite persistent storage for scans and findings
- Cloud scanner service supporting AWS (S3, IAM, VPC, Logging), GCP (Storage), Azure (Storage)
- REST API endpoints for scans, findings, health checks
- Role-based access control (viewer, operator, admin)
- JWT authentication with OIDC/Keycloak integration ready
- React + TypeScript + Vite frontend with Dashboard, Scans, Findings pages
- Real-time scan creation and monitoring
- Finding filtering by severity, category, cloud provider
- Pagination for findings lists
- Keycloak realm configuration for local development
- Docker Compose with backend, frontend, and Keycloak services
- GitHub Actions CI pipeline (backend tests, frontend tests, Docker builds)
- Comprehensive test suites (12+ backend tests, 3+ frontend tests)
- Portfolio.json manifest for GitHub portfolio integration

### Security
- Non-root Docker users
- HttpOnly cookie support ready
- CSRF protection ready
- Input validation on all API endpoints
- No hardcoded secrets

## [0.1.0] - 2026-10-13 (Initial CLI version)

### Added
- CLI-based cloud security scanner (main.py)
- AWS S3, IAM, VPC, CloudTrail scanning
- GCP Storage scanning
- Azure Storage scanning
- Severity scoring (critical, high, medium, low, info)
- JSON report export
- LLM-powered remediation guides
- Basic Docker support