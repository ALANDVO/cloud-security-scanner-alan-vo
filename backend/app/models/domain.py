from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..core.database import Base


class SeverityEnum(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class CloudEnum(str, enum.Enum):
    aws = "aws"
    gcp = "gcp"
    azure = "azure"


class ScanStatusEnum(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    cloud = Column(SQLEnum(CloudEnum), nullable=False, index=True)
    region = Column(String(64), nullable=True)
    category = Column(String(64), nullable=True)
    severity_filter = Column(String(16), nullable=True)
    status = Column(SQLEnum(ScanStatusEnum), default=ScanStatusEnum.pending, nullable=False, index=True)
    findings_count = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_scans_cloud_status", "cloud", "status"),
        Index("ix_scans_started_at", "started_at"),
    )


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id = Column(String(128), nullable=False, index=True)  # e.g., "aws-storage-bucket-name"
    severity = Column(SQLEnum(SeverityEnum), nullable=False, index=True)
    score = Column(Float, nullable=False)
    category = Column(String(64), nullable=False, index=True)
    resource = Column(String(256), nullable=False)
    title = Column(String(512), nullable=False)
    detail = Column(Text, nullable=False)
    remediation = Column(Text, nullable=False)
    cloud = Column(SQLEnum(CloudEnum), nullable=False, index=True)
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ai_analysis = Column(Text, nullable=True)

    scan = relationship("Scan", back_populates="findings")

    __table_args__ = (
        Index("ix_findings_scan_severity", "scan_id", "severity"),
    )