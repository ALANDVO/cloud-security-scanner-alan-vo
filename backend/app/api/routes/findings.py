from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from math import ceil

from ...core.database import get_db
from ...api.deps import require_role
from ...models.domain import Finding, SeverityEnum, CloudEnum
from ...models.schemas import FindingResponse, FindingListResponse

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("", response_model=FindingListResponse)
def list_findings(
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    cloud: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["viewer", "operator", "admin"])),
):
    query = db.query(Finding)

    if severity:
        try:
            query = query.filter(Finding.severity == SeverityEnum(severity))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")

    if category:
        query = query.filter(Finding.category == category)

    if cloud:
        try:
            query = query.filter(Finding.cloud == CloudEnum(cloud))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid cloud: {cloud}")

    total = query.count()
    findings = query.order_by(desc(Finding.score), desc(Finding.detected_at)).offset((page - 1) * page_size).limit(page_size).all()

    return FindingListResponse(
        findings=findings,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{finding_id}", response_model=FindingResponse)
def get_finding(
    finding_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["viewer", "operator", "admin"])),
):
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.get("/stats/summary")
def findings_summary(
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["viewer", "operator", "admin"])),
):
    total = db.query(func.count(Finding.id)).scalar() or 0

    by_severity = {}
    for sev in SeverityEnum:
        count = db.query(func.count(Finding.id)).filter(Finding.severity == sev).scalar() or 0
        by_severity[sev.value] = count

    by_category = {}
    cats = db.query(Finding.category, func.count(Finding.id)).group_by(Finding.category).all()
    for cat, count in cats:
        by_category[cat] = count

    by_cloud = {}
    for c in CloudEnum:
        count = db.query(func.count(Finding.id)).filter(Finding.cloud == c).scalar() or 0
        by_cloud[c.value] = count

    top_findings = db.query(Finding).order_by(desc(Finding.score)).limit(10).all()

    return {
        "total": total,
        "by_severity": by_severity,
        "by_category": by_category,
        "by_cloud": by_cloud,
        "top_findings": [
            {
                "id": f.id,
                "finding_id": f.finding_id,
                "severity": f.severity.value,
                "score": f.score,
                "category": f.category,
                "resource": f.resource,
                "title": f.title,
                "cloud": f.cloud.value,
            }
            for f in top_findings
        ],
    }