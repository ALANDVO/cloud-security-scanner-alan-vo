"""Tests for AI remediation service and API endpoints."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.domain import Finding, Scan, CloudEnum, ScanStatusEnum, SeverityEnum
from app.services.llm import (
    LLMService,
    OpenAICompatibleProvider,
    AnthropicProvider,
    GeminiProvider,
    LLMResponse,
)
from app.core.config import settings


class TestOpenAICompatibleProvider:
    def test_is_configured_with_key(self):
        provider = OpenAICompatibleProvider(api_key="test-key", base_url="https://api.openai.com/v1", model="gpt-4o")
        assert provider.is_configured() is True

    def test_is_configured_without_key(self):
        provider = OpenAICompatibleProvider(api_key="", base_url="https://api.openai.com/v1", model="gpt-4o")
        assert provider.is_configured() is False

    @pytest.mark.asyncio
    async def test_generate_success(self):
        provider = OpenAICompatibleProvider(api_key="test-key", base_url="https://api.openai.com/v1", model="gpt-4o")

        mock_response = {
            "choices": [{"message": {"content": "Test remediation guide"}}],
            "usage": {"total_tokens": 100},
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                raise_for_status=lambda: None,
                json=lambda: mock_response,
            )

            response = await provider.generate("Test prompt", system="System prompt")

        assert response.content == "Test remediation guide"
        assert response.provider == "openai-compatible"
        assert response.model == "gpt-4o"
        assert response.usage == {"total_tokens": 100}

    @pytest.mark.asyncio
    async def test_generate_http_error(self):
        provider = OpenAICompatibleProvider(api_key="test-key", base_url="https://api.openai.com/v1", model="gpt-4o")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                raise_for_status=lambda: (_ for _ in ()).throw(Exception("HTTP 401")),
            )

            with pytest.raises(Exception):
                await provider.generate("Test prompt")


class TestAnthropicProvider:
    def test_is_configured_with_key(self):
        provider = AnthropicProvider(api_key="test-key", base_url="https://api.anthropic.com", model="claude-3-opus")
        assert provider.is_configured() is True

    def test_is_configured_without_key(self):
        provider = AnthropicProvider(api_key="", base_url="https://api.anthropic.com", model="claude-3-opus")
        assert provider.is_configured() is False

    @pytest.mark.asyncio
    async def test_generate_success(self):
        provider = AnthropicProvider(api_key="test-key", base_url="https://api.anthropic.com", model="claude-3-opus")

        mock_response = {
            "content": [{"text": "Test remediation guide"}],
            "usage": {"input_tokens": 50, "output_tokens": 50},
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                raise_for_status=lambda: None,
                json=lambda: mock_response,
            )

            response = await provider.generate("Test prompt", system="System prompt")

        assert response.content == "Test remediation guide"
        assert response.provider == "anthropic"
        assert response.model == "claude-3-opus"


class TestGeminiProvider:
    def test_is_configured_with_key(self):
        provider = GeminiProvider(api_key="test-key", base_url="https://generativelanguage.googleapis.com", model="gemini-1.5-pro")
        assert provider.is_configured() is True

    def test_is_configured_without_key(self):
        provider = GeminiProvider(api_key="", base_url="https://generativelanguage.googleapis.com", model="gemini-1.5-pro")
        assert provider.is_configured() is False

    @pytest.mark.asyncio
    async def test_generate_success(self):
        provider = GeminiProvider(api_key="test-key", base_url="https://generativelanguage.googleapis.com", model="gemini-1.5-pro")

        mock_response = {
            "candidates": [{"content": {"parts": [{"text": "Test remediation guide"}]}}],
            "usageMetadata": {"totalTokenCount": 100},
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                raise_for_status=lambda: None,
                json=lambda: mock_response,
            )

            response = await provider.generate("Test prompt", system="System prompt")

        assert response.content == "Test remediation guide"
        assert response.provider == "gemini"
        assert response.model == "gemini-1.5-pro"


class TestLLMService:
    def test_init_default_provider(self):
        with patch.object(settings, "llm_provider", "openai"):
            with patch.object(settings, "llm_api_key", None):
                with patch.object(settings, "llm_base_url", None):
                    with patch.object(settings, "llm_model", "gpt-4o"):
                        service = LLMService()
                        assert service._provider is not None
                        assert isinstance(service._provider, OpenAICompatibleProvider)

    def test_init_anthropic_provider(self):
        with patch.object(settings, "llm_provider", "anthropic"):
            with patch.object(settings, "llm_api_key", "test-key"):
                with patch.object(settings, "llm_base_url", None):
                    with patch.object(settings, "llm_model", "claude-3-opus"):
                        service = LLMService()
                        assert isinstance(service._provider, AnthropicProvider)

    def test_init_gemini_provider(self):
        with patch.object(settings, "llm_provider", "gemini"):
            with patch.object(settings, "llm_api_key", "test-key"):
                with patch.object(settings, "llm_base_url", None):
                    with patch.object(settings, "llm_model", "gemini-1.5-pro"):
                        service = LLMService()
                        assert isinstance(service._provider, GeminiProvider)

    def test_is_configured_false_when_no_key(self):
        with patch.object(settings, "llm_provider", "openai"):
            with patch.object(settings, "llm_api_key", None):
                with patch.object(settings, "llm_base_url", None):
                    with patch.object(settings, "llm_model", "gpt-4o"):
                        service = LLMService()
                        assert service.is_configured() is False

    def test_get_provider_info(self):
        with patch.object(settings, "llm_provider", "openai"):
            with patch.object(settings, "llm_api_key", "test-key"):
                with patch.object(settings, "llm_base_url", None):
                    with patch.object(settings, "llm_model", "gpt-4o"):
                        service = LLMService()
                        info = service.get_provider_info()
                        assert info["configured"] is True
                        assert info["provider"] == "openai-compatible"
                        assert info["model"] == "gpt-4o"

    def test_fallback_remediation(self):
        with patch.object(settings, "llm_provider", "openai"):
            with patch.object(settings, "llm_api_key", None):
                service = LLMService()

                finding = {
                    "finding_id": "aws-storage-test-bucket",
                    "cloud": "aws",
                    "severity": "high",
                    "category": "storage",
                    "resource": "test-bucket",
                    "title": "S3 bucket public",
                    "detail": "Bucket allows public access",
                    "remediation": "Set bucket to private",
                }

                fallback = service._fallback_remediation(finding)
                assert "AI Analysis Unavailable" in fallback
                assert "S3 bucket public" in fallback
                assert "Set bucket to private" in fallback

    @pytest.mark.asyncio
    async def test_generate_remediation_unconfigured(self):
        with patch.object(settings, "llm_provider", "openai"):
            with patch.object(settings, "llm_api_key", None):
                service = LLMService()

                finding = {
                    "finding_id": "test-finding",
                    "cloud": "aws",
                    "severity": "high",
                    "category": "storage",
                    "resource": "test-resource",
                    "title": "Test finding",
                    "detail": "Test detail",
                    "remediation": "Test remediation",
                }

                result = await service.generate_remediation(finding)
                assert "AI Analysis Unavailable" in result
                assert "Demo Mode" in result


class TestAIRoutes:
    def test_get_ai_status_unconfigured(self, client, auth_headers):
        settings.oidc_enabled = True
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.get("/api/ai/status", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "configured" in data
        assert "provider" in data
        assert "model" in data

    def test_generate_remediation_not_found(self, client, auth_headers):
        settings.oidc_enabled = True
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["operator"]}
            response = client.post("/api/ai/remediation", json={"finding_id": 999}, headers=auth_headers)

        assert response.status_code == 404

    def test_generate_remediation_requires_operator(self, client, auth_headers):
        settings.oidc_enabled = True
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["viewer"]}
            response = client.post("/api/ai/remediation", json={"finding_id": 1}, headers=auth_headers)

        assert response.status_code == 403

    def test_generate_remediation_success(self, client, auth_headers, db_session):
        settings.oidc_enabled = True

        scan = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        finding = Finding(
            scan_id=scan.id,
            finding_id="aws-storage-test",
            severity=SeverityEnum.high,
            score=7.5,
            category="storage",
            resource="test-bucket",
            title="S3 bucket public",
            detail="Bucket allows public access",
            remediation="Set bucket to private",
            cloud=CloudEnum.aws,
        )
        db_session.add(finding)
        db_session.commit()
        db_session.refresh(finding)

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["operator"]}
            with patch("app.services.llm.llm_service.generate_remediation", new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = "# AI Remediation\n\n## 1. Threat Model\nTest analysis"
                response = client.post("/api/ai/remediation", json={"finding_id": finding.id}, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["finding_id"] == finding.id
        assert "AI Remediation" in data["ai_analysis"]

        # Verify it was stored
        db_session.refresh(finding)
        assert finding.ai_analysis is not None
        assert "AI Remediation" in finding.ai_analysis

    def test_generate_remediation_cached(self, client, auth_headers, db_session):
        settings.oidc_enabled = True

        scan = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        finding = Finding(
            scan_id=scan.id,
            finding_id="aws-storage-test2",
            severity=SeverityEnum.high,
            score=7.5,
            category="storage",
            resource="test-bucket2",
            title="S3 bucket public",
            detail="Bucket allows public access",
            remediation="Set bucket to private",
            cloud=CloudEnum.aws,
            ai_analysis="Existing AI analysis",
        )
        db_session.add(finding)
        db_session.commit()
        db_session.refresh(finding)

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["operator"]}
            with patch("app.services.llm.llm_service.generate_remediation", new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = "# AI Remediation\n\nNew analysis"
                response = client.post("/api/ai/remediation", json={"finding_id": finding.id, "regenerate": False}, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["ai_analysis"] == "Existing AI analysis"
        mock_gen.assert_not_called()

    def test_generate_remediation_regenerate(self, client, auth_headers, db_session):
        settings.oidc_enabled = True

        scan = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        finding = Finding(
            scan_id=scan.id,
            finding_id="aws-storage-test3",
            severity=SeverityEnum.high,
            score=7.5,
            category="storage",
            resource="test-bucket3",
            title="S3 bucket public",
            detail="Bucket allows public access",
            remediation="Set bucket to private",
            cloud=CloudEnum.aws,
            ai_analysis="Existing AI analysis",
        )
        db_session.add(finding)
        db_session.commit()
        db_session.refresh(finding)

        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["operator"]}
            with patch("app.services.llm.llm_service.generate_remediation", new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = "# AI Remediation\n\nNew analysis"
                response = client.post("/api/ai/remediation", json={"finding_id": finding.id, "regenerate": True}, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["ai_analysis"] == "# AI Remediation\n\nNew analysis"
        mock_gen.assert_called_once()

    def test_delete_remediation_admin_only(self, client, auth_headers, db_session):
        settings.oidc_enabled = True

        scan = Scan(cloud=CloudEnum.aws, status=ScanStatusEnum.completed)
        db_session.add(scan)
        db_session.commit()
        db_session.refresh(scan)

        finding = Finding(
            scan_id=scan.id,
            finding_id="aws-storage-test4",
            severity=SeverityEnum.high,
            score=7.5,
            category="storage",
            resource="test-bucket4",
            title="S3 bucket public",
            detail="Bucket allows public access",
            remediation="Set bucket to private",
            cloud=CloudEnum.aws,
            ai_analysis="Existing AI analysis",
        )
        db_session.add(finding)
        db_session.commit()
        db_session.refresh(finding)

        # Try with operator role - should fail
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["operator"]}
            response = client.delete(f"/api/ai/remediation/{finding.id}", headers=auth_headers)
        assert response.status_code == 403

        # Try with admin role - should succeed
        with patch("app.api.deps.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user1", "roles": ["admin"]}
            response = client.delete(f"/api/ai/remediation/{finding.id}", headers=auth_headers)
        assert response.status_code == 204

        db_session.refresh(finding)
        assert finding.ai_analysis is None