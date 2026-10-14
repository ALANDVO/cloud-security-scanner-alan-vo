from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from math import ceil

from ...core.database import get_db
from ...api.deps import require_role
from ...models.domain import Scan, Finding, ScanStatusEnum, SeverityEnum, CloudEnum
from ...models.schemas import ScanCreate, ScanResponse, FindingListResponse, FindingResponse, ScanSummary
from ...services.scanner import ScannerService

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
def create_scan(
    scan_in: ScanCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["operator", "admin"])),
):
    scanner = ScannerService(db)
    scan = scanner.run_scan(scan_in)
    return scan


@router.get("", response_model=List[ScanResponse])
def list_scans(
    cloud: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["viewer", "operator", "admin"])),
):
    query = db.query(Scan)
    if cloud:
        try:
            query = query.filter(Scan.cloud == CloudEnum(cloud))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid cloud: {cloud}")
    if status_filter:
        try:
            query = query.filter(Scan.status == ScanStatusEnum(status_filter))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")

    scans = query.order_by(desc(Scan.started_at)).offset(offset).limit(limit).all()
    return scans


@router.get("/summary", response_model=ScanSummary)
def get_summary(
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["viewer", "operator", "admin"])),
):
    total_scans = db.query(func.count(Scan.id)).scalar() or 0
    completed_scans = db.query(func.count(Scan.id)).filter(Scan.status == ScanStatusEnum.completed).scalar() or 0
    failed_scans = db.query(func.count(Scan.id)).filter(Scan.status == ScanStatusEnum.failed).scalar() or 0
    total_findings = db.query(func.count(Finding.id)).scalar() or 0

    by_severity = {}
    for sev in SeverityEnum:
        count = db.query(func.count(Finding.id)).filter(Finding.severity == sev).scalar() or 0
        by_severity[sev.value] = count

    by_cloud = {}
    for c in CloudEnum:
        count = db.query(func.count(Scan.id)).filter(Scan.cloud == c).scalar() or 0
        by_cloud[c.value] = count

    return ScanSummary(
        total_scans=total_scans,
        completed_scans=completed_scans,
        failed_scans=failed_scans,
        total_findings=total_findings,
        by_severity=by_severity,
        by_cloud=by_cloud,
    )


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["viewer", "operator", "admin"])),
):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/{scan_id}/findings", response_model=FindingListResponse)
def get_scan_findings(
    scan_id: int,
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["viewer", "operator", "admin"])),
):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    query = db.query(Finding).filter(Finding.scan_id == scan_id)

    if severity:
        try:
            query = query.filter(Finding.severity == SeverityEnum(severity))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")

    if category:
        query = query.filter(Finding.category == category)

    total = query.count()
    findings = query.order_by(Finding.score.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return FindingListResponse(
        findings=findings,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(["admin"])),
):
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    db.delete(scan)
    db.commit()