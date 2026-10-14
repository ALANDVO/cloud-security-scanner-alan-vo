import pytest
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.domain import Scan, Finding, SeverityEnum, CloudEnum, ScanStatusEnum
from app.models.schemas import ScanCreate, ScanResponse, FindingResponse


class TestDomainModels:
    def test_scan_creation(self, db_session: Session):
        scan = Scan(
            cloud=CloudEnum.aws,
            region="us-east-1",
            category="storage",
            status=ScanStatusEnum.pending,
        )
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        assert scan.id is not None
        assert scan.cloud == CloudEnum.aws
        assert scan.region == "us-east-1"
        assert scan.category == "storage"
        assert scan.status == ScanStatusEnum.pending
        assert scan.started_at is not None
        assert scan.findings_count == 0

    def test_finding_creation(self, db_session: Session):
        scan = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        finding = Finding(
            scan_id=scan.id,
            finding_id="aws-storage-test-bucket",
            severity=SeverityEnum.high,
            score=7.5,
            category="storage",
            resource="test-bucket",
            title="Test finding",
            detail="Test detail",
            remediation="Test remediation",
            cloud=CloudEnum.aws,
        )
        db_session.add(finding)
        db_session.commit()
        db_session.refresh(finding)

        assert finding.id is not None
        assert finding.scan_id == scan.id
        assert finding.severity == SeverityEnum.high
        assert finding.score == 7.5

    def test_scan_findings_relationship(self, db_session: Session):
        scan = Scan(cloud=CloudEnum.gcp, status=ScanStatusEnum.completed)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        for i in range(3):
            finding = Finding(
                scan_id=scan.id,
                finding_id=f"gcp-storage-bucket-{i}",
                severity=SeverityEnum.medium,
                score=5.0,
                category="storage",
                resource=f"bucket-{i}",
                title=f"Finding {i}",
                detail=f"Detail {i}",
                remediation=f"Fix {i}",
                cloud=CloudEnum.gcp,
            )
            db_session.add(finding)

        db_session.commit()

        scan_with_findings = db_session.query(Scan).filter(Scan.id == scan.id).first()
        assert len(scan_with_findings.findings) == 3

    def test_cascade_delete_findings(self, db_session: Session):
        scan = Scan(cloud=CloudEnum.azure, status=ScanStatusEnum.completed)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        finding = Finding(
            scan_id=scan.id,
            finding_id="azure-network-test",
            severity=SeverityEnum.critical,
            score=9.0,
            category="network",
            resource="test-resource",
            title="Critical finding",
            detail="Detail",
            remediation="Fix it",
            cloud=CloudEnum.azure,
        )
        db_session.add(finding)
        db_session.commit()

        db_session.delete(scan)
        db_session.commit()

        remaining = db_session.query(Finding).filter(Finding.scan_id == scan.id).all()
        assert len(remaining) == 0


class TestSchemas:
    def test_scan_create_schema(self):
        scan_in = ScanCreate(cloud=CloudEnum.aws, region="us-west-2", category="iam")
        assert scan_in.cloud == CloudEnum.aws
        assert scan_in.region == "us-west-2"
        assert scan_in.category == "iam"

    def test_scan_response_from_orm(self, db_session: Session):
        scan = Scan(
            cloud=CloudEnum.aws,
            region="us-east-1",
            status=ScanStatusEnum.completed,
            findings_count=5,
            critical_count=1,
            high_count=2,
            medium_count=2,
        )
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        response = ScanResponse.model_validate(scan)
        assert response.id == scan.id
        assert response.cloud == CloudEnum.aws
        assert response.findings_count == 5