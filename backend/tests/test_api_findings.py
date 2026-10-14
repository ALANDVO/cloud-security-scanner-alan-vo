import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.domain import Scan, Finding, CloudEnum, ScanStatusEnum, SeverityEnum
from app.core.config import settings


class TestFindingsAPI:
    def test_list_findings(self, client: TestClient, auth_headers, db_session: Session):
        settings.oidc_enabled = True
        scan = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        findings = [
            Finding(
                scan_id=scan.id,
                finding_id=f"aws-storage-bucket-{i}",
                severity=SeverityEnum.high if i % 2 == 0 else SeverityEnum.medium,
                score=7.5 if i % 2 == 0 else 5.0,
                category="storage",
                resource=f"bucket-{i}",
                title=f"Finding {i}",
                detail=f"Detail {i}",
                remediation=f"Fix {i}",
                cloud=CloudEnum.aws,
            )
            for i in range(5)
        ]
        db_session.add_all(findings)
        db_session.commit()

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.get("/api/findings", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 5
            assert len(data["findings"]) == 5
            assert data["page"] == 1
            assert data["page_size"] == 20

    def test_list_findings_filter_severity(self, client: TestClient, auth_headers, db_session: Session):
        settings.oidc_enabled = True
        scan = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        findings = [
            Finding(scan_id=scan.id, finding_id="f1", severity=SeverityEnum.critical, score=9.0, category="c", resource="r1", title="t1", detail="d1", remediation="r1", cloud=CloudEnum.aws),
            Finding(scan_id=scan.id, finding_id="f2", severity=SeverityEnum.high, score=7.5, category="c", resource="r2", title="t2", detail="d2", remediation="r2", cloud=CloudEnum.aws),
            Finding(scan_id=scan.id, finding_id="f3", severity=SeverityEnum.medium, score=5.0, category="c", resource="r3", title="t3", detail="d3", remediation="r3", cloud=CloudEnum.aws),
        ]
        db_session.add_all(findings)
        db_session.commit()

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.get("/api/findings?severity=high", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["findings"][0]["severity"] == "high"

    def test_list_findings_filter_category(self, client: TestClient, auth_headers, db_session: Session):
        settings.oidc_enabled = True
        scan = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        findings = [
            Finding(scan_id=scan.id, finding_id="f1", severity=SeverityEnum.high, score=7.5, category="storage", resource="r1", title="t1", detail="d1", remediation="r1", cloud=CloudEnum.aws),
            Finding(scan_id=scan.id, finding_id="f2", severity=SeverityEnum.high, score=7.5, category="iam", resource="r2", title="t2", detail="d2", remediation="r2", cloud=CloudEnum.aws),
        ]
        db_session.add_all(findings)
        db_session.commit()

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.get("/api/findings?category=storage", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["findings"][0]["category"] == "storage"

    def test_list_findings_filter_cloud(self, client: TestClient, auth_headers, db_session: Session):
        settings.oidc_enabled = True
        scan1 = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        scan2 = Scan(cloud=CloudEnum.gcp, status=ScanStatusEnum.completed)
        db_session.add_all([scan1, scan2])
        db_session.commit()
        db_session.refresh(scan1)
        db_session.refresh(scan2)

        findings = [
            Finding(scan_id=scan1.id, finding_id="f1", severity=SeverityEnum.high, score=7.5, category="storage", resource="r1", title="t1", detail="d1", remediation="r1", cloud=CloudEnum.aws),
            Finding(scan_id=scan2.id, finding_id="f2", severity=SeverityEnum.high, score=7.5, category="storage", resource="r2", title="t2", detail="d2", remediation="r2", cloud=CloudEnum.gcp),
        ]
        db_session.add_all(findings)
        db_session.commit()

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.get("/api/findings?cloud=gcp", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["findings"][0]["cloud"] == "gcp"

    def test_list_findings_pagination(self, client: TestClient, auth_headers, db_session: Session):
        settings.oidc_enabled = True
        scan = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        findings = [
            Finding(scan_id=scan.id, finding_id=f"f{i}", severity=SeverityEnum.high, score=7.5, category="c", resource=f"r{i}", title=f"t{i}", detail=f"d{i}", remediation=f"r{i}", cloud=CloudEnum.aws)
            for i in range(15)
        ]
        db_session.add_all(findings)
        db_session.commit()

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.get("/api/findings?page=1&page_size=5", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 15
            assert len(data["findings"]) == 5
            assert data["page"] == 1

            response = client.get("/api/findings?page=3&page_size=5", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert len(data["findings"]) == 5
            assert data["page"] == 3

    def test_get_finding(self, client: TestClient, auth_headers, db_session: Session):
        settings.oidc_enabled = True
        scan = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        finding = Finding(
            scan_id=scan.id,
            finding_id="aws-test-finding",
            severity=SeverityEnum.critical,
            score=9.0,
            category="storage",
            resource="test-bucket",
            title="Critical Finding",
            detail="Detail",
            remediation="Fix it",
            cloud=CloudEnum.aws,
        )
        db_session.add(finding)
        db_session.commit()
        db_session.refresh(finding)

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.get(f"/api/findings/{finding.id}", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == finding.id
            assert data["finding_id"] == "aws-test-finding"
            assert data["severity"] == "critical"

    def test_get_finding_not_found(self, client: TestClient, auth_headers):
        settings.oidc_enabled = True
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.get("/api/findings/99999", headers=auth_headers)
            assert response.status_code == 404

    def test_findings_summary(self, client: TestClient, auth_headers, db_session: Session):
        settings.oidc_enabled = True
        scan1 = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        scan2 = Scan(cloud=CloudEnum.gcp, status=ScanStatusEnum.completed)
        db_session.add_all([scan1, scan2])
        db_session.commit()
        db_session.refresh(scan1)
        db_session.refresh(scan2)

        findings = [
            Finding(scan_id=scan1.id, finding_id="f1", severity=SeverityEnum.critical, score=9.0, category="storage", resource="r1", title="t1", detail="d1", remediation="r1", cloud=CloudEnum.aws),
            Finding(scan_id=scan1.id, finding_id="f2", severity=SeverityEnum.high, score=7.5, category="iam", resource="r2", title="t2", detail="d2", remediation="r2", cloud=CloudEnum.aws),
            Finding(scan_id=scan2.id, finding_id="f3", severity=SeverityEnum.medium, score=5.0, category="network", resource="r3", title="t3", detail="d3", remediation="r3", cloud=CloudEnum.gcp),
        ]
        db_session.add_all(findings)
        db_session.commit()

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.get("/api/findings/stats/summary", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 3
            assert data["by_severity"]["critical"] == 1
            assert data["by_severity"]["high"] == 1
            assert data["by_severity"]["medium"] == 1
            assert data["by_category"]["storage"] == 1
            assert data["by_category"]["iam"] == 1
            assert data["by_category"]["network"] == 1
            assert data["by_cloud"]["aws"] == 2
            assert data["by_cloud"]["gcp"] == 1
            assert len(data["top_findings"]) == 3
            assert data["top_findings"][0]["severity"] == "critical"