# cloud-security-scanner-alan-vo

> Scans AWS, GCP, and Azure configurations for security misconfigurations across S3/GCS/Blob storage, IAM, VPC/networking, encryption, and logging — with severity scoring and remediation guides.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-React-3178C6)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)
![SSO](https://img.shields.io/badge/SSO-SAML%20%2F%20OAuth2-8A2BE2)
![License](https://img.shields.io/badge/License-MIT-green)
![AI](https://img.shields.io/badge/AI-Powered-purple)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

</div>

## Why cloud-security-scanner-alan-vo?

Scans AWS, GCP, and Azure configurations for security misconfigurations across S3/GCS/Blob storage, IAM, VPC/networking, encryption, and logging — with severity scoring and remediation guides.

Built by [Alan Vo](https://github.com/ALANDVO) — AI/ML & cybersecurity engineer.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     cloud-security-scanner-alan-vo                                    │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│  Frontend   │   API Layer │  Services   │   LLM Engine      │
│  React/TS   │  FastAPI    │  Domain     │  Multi-provider   │
│  Dashboard  │  SSO/SAML   │  Logic      │  OpenAI/Claude/   │
│  Real-time  │  JWT Auth   │  Processing │  Gemini/Ollama    │
└─────────────┴─────────────┴─────────────┴───────────────────┘
         │              │              │               │
         ▼              ▼              ▼               ▼
    ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────┐
    │ Browser │   │  REST   │   │  Domain │   │  LLM API    │
    │  SPA    │   │  API    │   │  Logic  │   │  (any)      │
    └─────────┘   └─────────┘   └─────────┘   └─────────────┘
```

## Features

- **S3/GCS/Blob public access and ACL auditing across all buckets**
- **IAM policy analysis: wildcard permissions, admin access, key age, unused roles**
- **VPC/network security: public subnets, open security groups, unencrypted traffic**
- **Encryption-at-rest verification for storage, databases, and volumes**
- **Logging and monitoring coverage checks (CloudTrail, Audit Logs, Activity Logs)**
- **CVE-style severity scoring (CVSS-like) with prioritized remediation guides**
- **Export findings to JSON/CSV for CI/CD security gates**

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
git clone https://github.com/ALANDVO/cloud-security-scanner-alan-vo.git
cd cloud-security-scanner-alan-vo
pip install -r requirements.txt
```

## Usage

```
python main.py scan --cloud aws --region us-east-1
python main.py scan --cloud aws --category storage --severity high
python main.py iam-audit --cloud aws
python main.py network-check --cloud aws --region us-east-1
python main.py remediate --finding s3-public-read
python main.py report --cloud aws --output report.json
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | LLM API key (OpenAI, Anthropic, Gemini) | Required |
| `LLM_BASE_URL` | Custom LLM endpoint (Ollama, vLLM) | `https://api.openai.com/v1` |
| `LLM_MODEL` | Model name | `gpt-4o` |
| `SAML_IDP_ENTITY` | SAML Identity Provider URL | — |
| `JWT_SECRET` | JWT signing secret | Generate one |

## Tech Stack

`Python` `AWS` `GCP` `Azure` `Security` `IAM` `Networking` `LLM`

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Login (SSO or email) |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/stats` | Statistics & metrics |
| `POST` | `/api/process` | Main processing endpoint |
| `GET` | `/api/results` | Query results |

## SSO Setup

### SAML
1. Set `SAML_IDP_ENTITY` to your IdP URL
2. Set `SAML_IDP_CERT` to your IdP certificate
3. Set `SAML_ACS_URL` to `https://yourdomain.com/saml/acs`

### OAuth2
1. Register your app with the OAuth provider
2. Set `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET`
3. Set `OAUTH_REDIRECT_URI`

## License

MIT — see [LICENSE](LICENSE)

---

**Built by [Alan Vo](https://github.com/ALANDVO)** | alanvo@gmail.com | AI, ML & Cybersecurity


