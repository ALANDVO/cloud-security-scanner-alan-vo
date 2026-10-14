import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from app.models.domain import Scan, Finding, CloudEnum, ScanStatusEnum, SeverityEnum
from app.models.schemas import ScanCreate
from app.services.scanner import ScannerService, SEVERITY_SCORES, SEVERITY_ORDER


class TestScannerService:
    def test_severity_scores(self):
        assert SEVERITY_SCORES["critical"] == 9.0
        assert SEVERITY_SCORES["high"] == 7.5
        assert SEVERITY_SCORES["medium"] == 5.0
        assert SEVERITY_SCORES["low"] == 2.5
        assert SEVERITY_SCORES["info"] == 1.0

    def test_severity_order(self):
        assert SEVERITY_ORDER["critical"] == 0
        assert SEVERITY_ORDER["high"] == 1
        assert SEVERITY_ORDER["medium"] == 2
        assert SEVERITY_ORDER["low"] == 3
        assert SEVERITY_ORDER["info"] == 4

    def test_add_finding(self, db_session: Session):
        scanner = ScannerService(db_session)
        finding = scanner._add_finding(
            severity="high",
            category="storage",
            resource="test-bucket",
            title="Test Finding",
            detail="Test detail",
            remediation="Fix it",
            cloud="aws",
        )

        assert finding["severity"] == "high"
        assert finding["score"] == 7.5
        assert finding["category"] == "storage"
        assert finding["resource"] == "test-bucket"
        assert finding["cloud"] == "aws"
        assert "detected_at" in finding

    def test_add_finding_unknown_severity(self, db_session: Session):
        scanner = ScannerService(db_session)
        finding = scanner._add_finding(
            severity="unknown",
            category="test",
            resource="test",
            title="Test",
            detail="Detail",
            remediation="Fix",
            cloud="aws",
        )
        assert finding["score"] == 1.0

    @patch("app.services.scanner.boto3.Session")
    def test_scan_aws_s3_mock(self, mock_boto_session, db_session: Session):
        mock_s3 = MagicMock()
        mock_boto_session.return_value.client.return_value = mock_s3

        mock_s3.list_buckets.return_value = {"Buckets": [{"Name": "test-bucket"}]}
        mock_s3.get_bucket_acl.return_value = {
            "Grants": [{"Grantee": {"URI": "http://acs.amazonaws.com/groups/global/AllUsers"}}]
        }
        mock_s3.get_public_access_block.return_value = {
            "PublicAccessBlockAssignment": {"BlockPublicAcls": False}
        }
        mock_s3.get_bucket_encryption.side_effect = Exception("No encryption")

        scanner = ScannerService(db_session)
        scan = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.running)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        scanner.scan_aws(scan, category="storage")

        findings = scanner.findings_buffer
        assert len(findings) == 3
        severities = [f["severity"] for f in findings]
        assert "critical" in severities
        assert "high" in severities
        assert "medium" in severities

    @patch("app.services.scanner.boto3.Session")
    def test_scan_aws_iam_mock(self, mock_boto_session, db_session: Session):
        mock_iam = MagicMock()
        mock_boto_session.return_value.client.return_value = mock_iam

        mock_iam.list_roles.return_value = {
            "Roles": [{"RoleName": "AdminRole", "Arn": "arn:aws:iam::123456789012:role/AdminRole"}]
        }
        mock_iam.list_users.return_value = {"Users": [{"UserName": "test-user"}]}
        mock_iam.list_access_keys.return_value = {
            "AccessKeyMetadata": [
                {"AccessKeyId": "AKIA123", "Status": "Active", "CreateDate": "2020-01-01T00:00:00Z"}
            ]
        }
        mock_iam.list_policies.return_value = {
            "Policies": [
                {"PolicyName": "AdminPolicy", "AttachmentCount": 5},
                {"PolicyName": "ReadOnlyPolicy", "AttachmentCount": 1},
            ]
        }

        scanner = ScannerService(db_session)
        scan = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.running)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        scanner.scan_aws(scan, category="iam")

        findings = scanner.findings_buffer
        assert len(findings) >= 2
        categories = [f["category"] for f in findings]
        assert "iam" in categories

    def test_run_scan_creates_scan_record(self, db_session: Session):
        scanner = ScannerService(db_session)

        with patch.object(scanner, "scan_aws") as mock_scan:
            scan_create = ScanCreate(cloud=CloudEnum.aws, region="us-east-1", category="storage")
            scan = scanner.run_scan(scan_create)

            assert scan.id is not None
            assert scan.cloud == CloudEnum.aws
            assert scan.region == "us-east-1"
            assert scan.category == "storage"
            assert scan.status == ScanStatusEnum.completed
            assert scan.completed_at is not None

    def test_run_scan_handles_error(self, db_session: Session, test_engine):
        scanner = ScannerService(db_session)

        with patch.object(scanner, "scan_aws", side_effect=Exception("AWS error")):
            scan_create = ScanCreate(cloud=CloudEnum.aws)
            with pytest.raises(Exception):
                scanner.run_scan(scan_create)

        # Use a new session to query the committed scan
        from sqlalchemy.orm import sessionmaker
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        new_session = TestingSessionLocal()
        try:
            failed_scan = new_session.query(Scan).filter(Scan.status == ScanStatusEnum.failed).first()
            assert failed_scan is not None
            assert failed_scan.error_message == "AWS error"
        finally:
            new_session.close()

    def test_severity_filter(self, db_session: Session):
        scanner = ScannerService(db_session)

        scanner._add_finding("critical", "cat", "res1", "t1", "d1", "r1", "aws")
        scanner._add_finding("high", "cat", "res2", "t2", "d2", "r2", "aws")
        scanner._add_finding("medium", "cat", "res3", "t3", "d3", "r3", "aws")
        scanner._add_finding("low", "cat", "res4", "t4", "d4", "r4", "aws")

        from app.models.schemas import Severity as SchemaSeverity
        filtered = [f for f in scanner.findings_buffer if SEVERITY_ORDER.get(f["severity"], 5) <= SEVERITY_ORDER["high"]]
        assert len(filtered) == 2
        assert all(f["severity"] in ["critical", "high"] for f in filtered)