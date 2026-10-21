# cloud-security-scanner-alan-vo — Alan Vo

> Work in progress. This checkpoint may be incomplete or fail tests. See PLAN.md and STATUS.md before use.


> Multi-cloud security misconfiguration scanner with FastAPI backend, React dashboard, and AI-powered remediation guides for AWS, GCP, and Azure — Alan Vo | AI & Machine Learning

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688)
![React](https://img.shields.io/badge/React-18-61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)
![Keycloak](https://img.shields.io/badge/Keycloak-OIDC-8A2BE2)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

</div>

## Why cloud-security-scanner-alan-vo?

Scans AWS, GCP, and Azure configurations for security misconfigurations across S3/GCS/Blob storage, IAM, VPC/networking, encryption, and logging — with severity scoring and AI-powered remediation guides.

Built by [Alan Vo](https://github.com/ALANDVO) — AI/ML & cybersecurity engineer.

## Architecture

```mermaid
graph TB
    subgraph Frontend
        UI[React + TypeScript SPA]
        API_CLIENT[Typed API Client]
        STATE[Zustand State]
    end

    subgraph Backend
        FASTAPI[FastAPI App]
        SCANS_API[/api/scans]
        FINDINGS_API[/api/findings]
        HEALTH_API[/api/health]
        AUTH[JWT + OIDC Auth]
        SCANNER[Scanner Service]
        DB[(SQLite)]
    end

    subgraph Cloud
        AWS[AWS APIs]
        GCP[GCP APIs]
        AZURE[Azure APIs]
    end

    subgraph Identity
        KC[Keycloak OIDC]
    end

    UI --> API_CLIENT
    API_CLIENT --> FASTAPI
    FASTAPI --> SCANS_API
    FASTAPI --> FINDINGS_API
    FASTAPI --> HEALTH_API
    FASTAPI --> AUTH
    AUTH --> KC
    SCANS_API --> SCANNER
    FINDINGS_API --> DB
    SCANNER --> DB
    SCANNER --> AWS
    SCANNER --> GCP
    SCANNER --> AZURE
```

## Features

- **Multi-cloud scanning**: AWS (S3, IAM, VPC, CloudTrail), GCP (Storage), Azure (Storage)
- **Severity scoring**: CVSS-like critical/high/medium/low/info classification
- **Persistent storage**: SQLite with SQLAlchemy for scans and findings history
- **REST API**: Full CRUD for scans and findings with pagination and filtering
- **Role-based access**: Viewer, Operator, Admin roles with JWT/OIDC authentication
- **Real-time dashboard**: Scan statistics, severity breakdown, top findings
- **AI remediation**: LLM-powered analysis for top findings (OpenAI, Anthropic, Gemini, Ollama)
- **Docker Compose**: One-command deployment with Keycloak for SSO
- **CI/CD**: GitHub Actions with backend/frontend tests and Docker builds

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/ALANDVO/cloud-security-scanner-alan-vo.git
cd cloud-security-scanner-alan-vo
cp .env.example .env
docker compose up -d
# Open http://localhost:3000
```

### Local Development

```bash
# Backend
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Usage

### API Endpoints

| Method | Endpoint | Description | Roles |
|--------|----------|-------------|-------|
| `GET` | `/api/health` | Health check | All |
| `GET` | `/api/scans/summary` | Scan statistics | All |
| `GET` | `/api/scans` | List scans with filters | All |
| `POST` | `/api/scans` | Create new scan | Operator, Admin |
| `GET` | `/api/scans/{id}` | Get scan details | All |
| `GET` | `/api/scans/{id}/findings` | Get scan findings | All |
| `DELETE` | `/api/scans/{id}` | Delete scan | Admin |
| `GET` | `/api/findings` | List all findings | All |
| `GET` | `/api/findings/stats/summary` | Findings statistics | All |
| `GET` | `/api/ai/status` | AI provider status | All |
| `POST` | `/api/ai/remediation` | Generate AI remediation for finding | Operator, Admin |
| `POST` | `/api/ai/executive-summary` | Generate AI executive summary for scan | All |
| `DELETE` | `/api/ai/remediation/{id}` | Delete AI remediation | Admin |
### Demo Accounts (Keycloak)

| Username | Password | Role |
|----------|----------|------|
| viewer | viewer123 | Read-only |
| operator | operator123 | Create scans |
| admin | admin123 | Full access |

### Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database path | `sqlite:///./data/scanner.db` |
| `SECRET_KEY` | JWT signing secret | Generate one |
| `LLM_API_KEY` | LLM API key | Required for AI features |
| `LLM_BASE_URL` | Custom LLM endpoint | `https://api.openai.com/v1` |
| `LLM_MODEL` | Model name | `gpt-4o` |
| `LLM_PROVIDER` | Provider type | `openai` |
| `OIDC_ENABLED` | Enable OIDC auth | `false` |
| `OIDC_ISSUER_URL` | Keycloak realm URL | `http://localhost:8080/realms/cloud-scanner` |
| `AWS_REGION` | AWS region | `us-east-1` |

## AI/ML Evaluation

The scanner includes AI-powered remediation and executive summary engines that use LLMs to generate contextual remediation guides for security findings and executive summaries for scans.

### Reproducible Evaluation

```bash
# Set LLM credentials
export LLM_API_KEY=your-key
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4o

# Run scan with AI analysis
python -c "
from backend.app.services.scanner import ScannerService
from backend.app.models.schemas import ScanCreate
from backend.app.core.database import SessionLocal
from backend.app.models.domain import CloudEnum

db = SessionLocal()
scanner = ScannerService(db)
scan = scanner.run_scan(ScanCreate(cloud=CloudEnum.aws, category='storage'))
print(f'Scan {scan.id}: {scan.findings_count} findings')
for f in scan.findings[:3]:
    print(f'  {f.severity.value}: {f.title}')
"

# Generate AI executive summary for a scan
python -c "
from backend.app.services.llm import llm_service
from backend.app.core.database import SessionLocal
from backend.app.models.domain import Scan, Finding, CloudEnum, ScanStatusEnum, SeverityEnum
import asyncio

db = SessionLocal()
scan = db.query(Scan).filter(Scan.id == 1).first()
if scan:
    findings = scan.findings
    finding_data = [
        {
            'finding_id': f.finding_id,
            'cloud': f.cloud.value,
            'severity': f.severity.value,
            'category': f.category,
            'resource': f.resource,
            'title': f.title,
            'detail': f.detail,
            'remediation': f.remediation,
            'score': f.score,
        }
        for f in findings
    ]
    scan_data = {
        'cloud': scan.cloud.value,
        'region': scan.region,
        'category': scan.category,
        'started_at': scan.started_at.isoformat() if scan.started_at else None,
        'findings_count': scan.findings_count,
        'severity_counts': {
            'critical': scan.critical_count,
            'high': scan.high_count,
            'medium': scan.medium_count,
            'low': scan.low_count,
            'info': scan.info_count,
        },
        'by_category': {},
        'by_cloud': {scan.cloud.value: scan.findings_count},
        'findings': finding_data,
    }
    for f in findings:
        cat = f.category
        scan_data['by_category'][cat] = scan_data['by_category'].get(cat, 0) + 1
    summary = asyncio.run(llm_service.generate_executive_summary(scan_data))
    print(summary[:500])
"
```

### Baseline Metrics (Local Testing)

| Cloud | Categories Tested | Findings Detected | AI Analysis Time |
|-------|------------------|-------------------|------------------|
| AWS | storage, iam, network, logging | Varies by account | ~2-5s per finding / ~5-10s per summary |
| GCP | storage | Varies by project | ~2-5s per finding / ~5-10s per summary |
| Azure | storage | Varies by subscription | ~2-5s per finding / ~5-10s per summary |

### Limitations

- Requires valid cloud credentials for real scanning (uses boto3, google-cloud, azure-identity)
- AI analysis is advisory only — always verify remediation commands before execution
- Mock mode available for development without cloud credentials
- LLM responses may vary; not deterministic
## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Pydantic, python-jose, passlib
- **Frontend**: React 18, TypeScript, Vite, TanStack Query, Zustand, Tailwind CSS
- **Auth**: Keycloak OIDC with PKCE, JWT tokens
- **Database**: SQLite (dev), PostgreSQL-ready
- **Cloud SDKs**: boto3, google-cloud-storage, azure-identity
- **Testing**: pytest, vitest, React Testing Library
- **CI/CD**: GitHub Actions, Docker

## SSO Setup

### Keycloak (Local)

```bash
docker compose up -d keycloak
# Open http://localhost:8080 (admin/admin)
# Realm 'cloud-scanner' pre-configured with clients and users
```

### SAML via Keycloak Broker

1. Configure SAML Identity Provider in Keycloak Admin Console
2. Set `OIDC_ISSUER_URL` to your Keycloak realm
3. Map SAML attributes to Keycloak roles (viewer, operator, admin)

## License

MIT — see [LICENSE](LICENSE)

---

**Built by [Alan Vo](https://github.com/ALANDVO)** | alanvo@gmail.com | AI, ML & Cybersecurity