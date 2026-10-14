"""AI remediation API endpoints."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...api.deps import require_role
from ...models.domain import Finding
from ...models.schemas import AIRemediationRequest, AIRemediationResponse, AIProviderStatus
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
            finding_id=finding.id,
            ai_analysis=finding.ai_analysis,
            provider=llm_service.get_provider_info().get("provider", "unknown"),
            model=llm_service.get_provider_info().get("model", "unknown"),
            generated_at=finding.detected_at,
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
    finding.ai_analysis = ai_analysis
    db.commit()

    return AIRemediationResponse(
        finding_id=finding.id,
        ai_analysis=ai_analysis,
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

    finding.ai_analysis = None
    db.commit()