from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class Cloud(str, Enum):
    aws = "aws"
    gcp = "gcp"
    azure = "azure"


class ScanStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class ScanCreate(BaseModel):
    cloud: Cloud
    region: Optional[str] = "us-east-1"
    category: Optional[str] = None
    severity_filter: Optional[Severity] = None


class ScanResponse(BaseModel):
    id: int
    cloud: Cloud
    region: Optional[str]
    category: Optional[str]
    severity_filter: Optional[Severity]
    status: ScanStatus
    findings_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    started_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class FindingResponse(BaseModel):
    id: int
    scan_id: int
    finding_id: str
    severity: Severity
    score: float
    category: str
    resource: str
    title: str
    detail: str
    remediation: str
    cloud: Cloud
    detected_at: datetime
    ai_analysis: Optional[str]

    class Config:
        from_attributes = True


class FindingListResponse(BaseModel):
    findings: List[FindingResponse]
    total: int
    page: int
    page_size: int


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str


class ScanSummary(BaseModel):
    total_scans: int
    completed_scans: int
    failed_scans: int
    total_findings: int
    by_severity: dict
    by_cloud: dict


class AIRemediationRequest(BaseModel):
    finding_id: int
    regenerate: bool = False


class AIRemediationResponse(BaseModel):
    finding_id: int
    ai_analysis: str
    provider: str
    model: str
    generated_at: datetime


class AIProviderStatus(BaseModel):
    configured: bool
    provider: str
    model: str


class AIExecutiveSummaryRequest(BaseModel):
    scan_id: int
    regenerate: bool = False

class AIExecutiveSummaryResponse(BaseModel):
    scan_id: int
    ai_summary: str
    provider: str
    model: str
    generated_at: datetime