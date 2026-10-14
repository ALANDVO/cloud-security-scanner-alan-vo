import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.domain import Scan, Finding, CloudEnum, ScanStatusEnum, SeverityEnum
from app.core.config import settings


class TestScansAPI:
    def test_health_endpoint(self, client: TestClient):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["version"] == settings.app_version
        assert "database" in data

    def test_create_scan_unauthorized(self, client: TestClient):
        settings.oidc_enabled = True
        response = client.post("/api/scans", json={"cloud": "aws", "region": "us-east-1"})
        assert response.status_code == 401

    def test_create_scan_requires_operator_role(self, client: TestClient, auth_headers):
        settings.oidc_enabled = True
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.post(
                "/api/scans",
                json={"cloud": "aws", "region": "us-east-1"},
                headers=auth_headers,
            )
            assert response.status_code == 403

    def test_create_scan_success(self, client: TestClient, auth_headers, db_session: Session):
        settings.oidc_enabled = True
        with patch("app.api.deps.verify_token") as mock_verify, \
             patch("app.services.scanner.ScannerService.scan_aws") as mock_scan:
            mock_verify.return_value = {"sub": "user1", "roles": ["operator"]}
            
            response = client.post(
                "/api/scans",
                json={"cloud": "aws", "region": "us-east-1", "category": "storage"},
                headers=auth_headers,
            )
            assert response.status_code == 201
            data = response.json()
            assert data["cloud"] == "aws"
            assert data["region"] == "us-east-1"
            assert data["category"] == "storage"
            assert data["status"] == "completed"
            assert data["id"] is not None

    def test_create_scan_invalid_cloud(self, client: TestClient, auth_headers):
        settings.oidc_enabled = True
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["operator"]}
            response = client.post(
                "/api/scans",
                json={"cloud": "invalid", "region": "us-east-1"},
                headers=auth_headers,
            )
            assert response.status_code == 422

    def test_list_scans(self, client: TestClient, auth_headers, db_session: Session):
        settings.oidc_enabled = True
        scan1 = Scan(cloud=CloudEnum.aws, region="us-east-1", status=ScanStatusEnum.completed)
        scan2 = Scan(cloud=CloudEnum.gcp, region="us-central1", status=ScanStatusEnum.pending)
        db_session.add_all([scan1, scan2])
        db_session.commit()

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.get("/api/scans", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2

    def test_list_scans_filter_by_cloud(self, client: TestClient, auth_headers, db_session: Session):
        settings.oidc_enabled = True
        scan1 = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        scan2 = Scan(cloud=CloudEnum.gcp, status=ScanStatusEnum.completed)
        db_session.add_all([scan1, scan2])
        db_session.commit()

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.get("/api/scans?cloud=aws", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["cloud"] == "aws"

    def test_list_scans_filter_by_status(self, client: TestClient, auth_headers, db_session: Session):
        settings.oidc_enabled = True
        scan1 = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        scan2 = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.pending)
        db_session.add_all([scan1, scan2])
        db_session.commit()

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.get("/api/scans?status=completed", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["status"] == "completed"

    def test_get_scan(self, client: TestClient, auth_headers, db_session: Session):
        settings.oidc_enabled = True
        scan = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed, findings_count=5)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.get(f"/api/scans/{scan.id}", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == scan.id
            assert data["findings_count"] == 5

    def test_get_scan_not_found(self, client: TestClient, auth_headers):
        settings.oidc_enabled = True
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.get("/api/scans/99999", headers=auth_headers)
            assert response.status_code == 404

    def test_get_scan_summary(self, client: TestClient, auth_headers, db_session: Session):
        settings.oidc_enabled = True
        scan1 = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        scan2 = Scan(cloud=CloudEnum.gcp, status=ScanStatusEnum.failed)
        db_session.add_all([scan1, scan2])
        db_session.commit()

        finding = Finding(
            scan_id=scan1.id,
            finding_id="aws-test",
            severity=SeverityEnum.high,
            score=7.5,
            category="storage",
            resource="bucket",
            title="Test",
            detail="Detail",
            remediation="Fix",
            cloud=CloudEnum.aws,
        )
        db_session.add(finding)
        db_session.commit()

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.get("/api/scans/summary", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total_scans"] == 2
            assert data["completed_scans"] == 1
            assert data["failed_scans"] == 1
            assert data["total_findings"] == 1
            assert "by_severity" in data
            assert "by_cloud" in data

    def test_delete_scan_admin_only(self, client: TestClient, auth_headers, db_session: Session):
        settings.oidc_enabled = True
        scan = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["operator"]}
            response = client.delete(f"/api/scans/{scan.id}", headers=auth_headers)
            assert response.status_code == 403

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "admin1", "roles": ["admin"]}
            response = client.delete(f"/api/scans/{scan.id}", headers=auth_headers)
            assert response.status_code == 204

            check = db_session.query(Scan).filter(Scan.id == scan.id).first()
            assert check is None