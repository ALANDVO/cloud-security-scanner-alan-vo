"""AI remediation API endpoints."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...api.deps import require_role
from ...models.domain import Finding, Scan
from ...models.schemas import (
    AIRemediationRequest,
    AIRemediationResponse,
    AIProviderStatus,
    AIExecutiveSummaryRequest,
    AIExecutiveSummaryResponse,
)
from ...services.llm import llm_service

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status", response_model=AIProviderStatus)
def get_ai_status(user: dict = Depends(require_role(["viewer", "operator", "admin"]))):
    """Get AI provider configuration status."""
    info = llm_service.get_provider_info()
    return AIProviderStatus(**info)


@router.post("/remediation", response_model=AIRemediationResponse)
async def generate_remediation(
    request: AIRemediationRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["operator", "admin"])),
):
    """Generate AI-powered remediation analysis for a finding."""
    finding = db.query(Finding).filter(Finding.id == request.finding_id).first()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    # Check if AI analysis already exists and regenerate is False
    if finding.ai_analysis and not request.regenerate:
        return AIRemediationResponse(
            finding_id=finding.id,  # type: ignore[arg-type]
            ai_analysis=finding.ai_analysis,  # type: ignore[arg-type]
            provider=llm_service.get_provider_info().get("provider", "unknown"),
            model=llm_service.get_provider_info().get("model", "unknown"),
            generated_at=finding.detected_at,  # type: ignore[arg-type]
        )

    # Prepare finding data for LLM
    finding_data = {
        "finding_id": finding.finding_id,
        "cloud": finding.cloud.value,
        "severity": finding.severity.value,
        "category": finding.category,
        "resource": finding.resource,
        "title": finding.title,
        "detail": finding.detail,
        "remediation": finding.remediation,
    }

    # Generate AI analysis
    ai_analysis = await llm_service.generate_remediation(finding_data)

    # Store in database
    finding.ai_analysis = ai_analysis  # type: ignore[assignment]
    db.commit()

    return AIRemediationResponse(
        finding_id=finding.id,  # type: ignore[arg-type]
        ai_analysis=ai_analysis,
        provider=llm_service.get_provider_info().get("provider", "unknown"),
        model=llm_service.get_provider_info().get("model", "unknown"),
        generated_at=datetime.utcnow(),
    )


@router.post("/executive-summary", response_model=AIExecutiveSummaryResponse)
async def generate_executive_summary(
    request: AIExecutiveSummaryRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["viewer", "operator", "admin"])),
):
    """Generate AI-powered executive summary for a scan."""
    scan = db.query(Scan).filter(Scan.id == request.scan_id).first()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    # Check if AI summary already exists and regenerate is False
    if scan.ai_summary and not request.regenerate:
        return AIExecutiveSummaryResponse(
            scan_id=scan.id,  # type: ignore[arg-type]
            ai_summary=scan.ai_summary,  # type: ignore[arg-type]
            provider=llm_service.get_provider_info().get("provider", "unknown"),
            model=llm_service.get_provider_info().get("model", "unknown"),
            generated_at=scan.completed_at or scan.started_at,  # type: ignore[arg-type]
        )

    # Prepare scan data for LLM
    findings = scan.findings
    finding_data = [
        {
            "finding_id": f.finding_id,
            "cloud": f.cloud.value,
            "severity": f.severity.value,
            "category": f.category,
            "resource": f.resource,
            "title": f.title,
            "detail": f.detail,
            "remediation": f.remediation,
            "score": f.score,
        }
        for f in findings
    ]

    scan_data = {
        "cloud": scan.cloud.value,
        "region": scan.region,
        "category": scan.category,
        "started_at": scan.started_at.isoformat() if scan.started_at else None,
        "findings_count": scan.findings_count,
        "severity_counts": {
            "critical": scan.critical_count,
            "high": scan.high_count,
            "medium": scan.medium_count,
            "low": scan.low_count,
            "info": scan.info_count,
        },
        "by_category": {},
        "by_cloud": {scan.cloud.value: scan.findings_count},
        "findings": finding_data,
    }

    # Aggregate by category
    for f in findings:
        cat = f.category
        scan_data["by_category"][cat] = scan_data["by_category"].get(cat, 0) + 1

    # Generate AI executive summary
    ai_summary = await llm_service.generate_executive_summary(scan_data)

    # Store in database
    scan.ai_summary = ai_summary  # type: ignore[assignment]
    db.commit()

    return AIExecutiveSummaryResponse(
        scan_id=scan.id,  # type: ignore[arg-type]
        ai_summary=ai_summary,
        provider=llm_service.get_provider_info().get("provider", "unknown"),
        model=llm_service.get_provider_info().get("model", "unknown"),
        generated_at=datetime.utcnow(),
    )


@router.delete("/remediation/{finding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_remediation(
    finding_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["admin"])),
):
    """Delete AI remediation analysis for a finding (admin only)."""
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    finding.ai_analysis = None  # type: ignore[assignment]
    db.commit()