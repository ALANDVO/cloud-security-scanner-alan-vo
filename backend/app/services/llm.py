"""LLM service with multi-provider support for AI-powered remediation analysis."""
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import httpx
from ..core.config import settings


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    usage: Optional[dict] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, system: str = "", temperature: float = 0.3, max_tokens: int = 2048) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        pass


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible provider (OpenAI, LiteLLM, OpenRouter, Ollama)."""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def generate(self, prompt: str, system: str = "", temperature: float = 0.3, max_tokens: int = 2048) -> LLMResponse:
        if not self.is_configured():
            raise ValueError("OpenAI-compatible provider not configured: missing API key")

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            provider="openai-compatible",
            model=self.model,
            usage=data.get("usage"),
        )


class AnthropicProvider(LLMProvider):
    """Anthropic Messages API provider."""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def generate(self, prompt: str, system: str = "", temperature: float = 0.3, max_tokens: int = 2048) -> LLMResponse:
        if not self.is_configured():
            raise ValueError("Anthropic provider not configured: missing API key")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        messages = [{"role": "user", "content": prompt}]
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/v1/messages", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        return LLMResponse(
            content=data["content"][0]["text"],
            provider="anthropic",
            model=self.model,
            usage=data.get("usage"),
        )


class GeminiProvider(LLMProvider):
    """Google Gemini generateContent API provider."""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def generate(self, prompt: str, system: str = "", temperature: float = 0.3, max_tokens: int = 2048) -> LLMResponse:
        if not self.is_configured():
            raise ValueError("Gemini provider not configured: missing API key")

        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}

        content = f"{system}\n\n{prompt}" if system else prompt
        payload = {
            "contents": [{"parts": [{"text": content}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }

        url = f"{self.base_url}/models/{self.model}:generateContent"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, params=params, json=payload)
            response.raise_for_status()
            data = response.json()

        content_text = data["candidates"][0]["content"]["parts"][0]["text"]

        return LLMResponse(
            content=content_text,
            provider="gemini",
            model=self.model,
            usage=data.get("usageMetadata"),
        )


class LLMService:
    """Main LLM service that manages provider selection and generation."""

    def __init__(self):
        self._provider: Optional[LLMProvider] = None
        self._init_provider()

    def _init_provider(self) -> None:
        """Initialize the LLM provider based on configuration."""
        provider_type = settings.llm_provider.lower()
        api_key = settings.llm_api_key
        base_url = settings.llm_base_url
        model = settings.llm_model

        if provider_type == "anthropic":
            if not base_url:
                base_url = "https://api.anthropic.com"
            self._provider = AnthropicProvider(api_key=api_key or "", base_url=base_url, model=model)
        elif provider_type == "gemini":
            if not base_url:
                base_url = "https://generativelanguage.googleapis.com"
            self._provider = GeminiProvider(api_key=api_key or "", base_url=base_url, model=model)
        else:  # openai-compatible (default)
            if not base_url:
                base_url = "https://api.openai.com/v1"
            self._provider = OpenAICompatibleProvider(api_key=api_key or "", base_url=base_url, model=model)

    def is_configured(self) -> bool:
        """Check if the current provider is configured."""
        return self._provider is not None and self._provider.is_configured()

    def get_provider_info(self) -> dict:
        """Get information about the current provider."""
        if not self._provider:
            return {"configured": False, "provider": "none", "model": ""}
        provider_name = type(self._provider).__name__.replace("Provider", "").lower()
        # Normalize provider names
        if provider_name == "openaicompatible":
            provider_name = "openai-compatible"
        return {
            "configured": self._provider.is_configured(),
            "provider": provider_name,
            "model": self._provider.model,
        }

    async def generate_remediation(self, finding_data: dict) -> str:
        """Generate AI-powered remediation guide for a security finding."""
        if not self.is_configured():
            return self._fallback_remediation(finding_data)

        system_prompt = (
            "You are a cloud security expert specializing in AWS, GCP, and Azure security. "
            "Provide concise, actionable remediation guides for security findings. "
            "Format your response as markdown with clear sections. "
            "Never fabricate commands - use real CLI syntax for the relevant cloud provider."
        )

        prompt = self._build_remediation_prompt(finding_data)

        try:
            response = await self._provider.generate(prompt, system=system_prompt, temperature=0.2, max_tokens=3000)
            return response.content
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json().get("error", {}).get("message", str(e))
            except Exception:
                error_detail = str(e)
            return f"**AI Analysis Unavailable** (Provider error: {error_detail})\n\n{self._fallback_remediation(finding_data)}"
        except Exception as e:
            return f"**AI Analysis Unavailable** ({type(e).__name__}: {str(e)})\n\n{self._fallback_remediation(finding_data)}"

    def _build_remediation_prompt(self, finding: dict) -> str:
        """Build a detailed prompt for remediation generation."""
        return f"""
Security Finding Details:
- **Finding ID**: {finding.get('finding_id', 'N/A')}
- **Cloud Provider**: {finding.get('cloud', 'unknown').upper()}
- **Severity**: {finding.get('severity', 'unknown').upper()}
- **Category**: {finding.get('category', 'unknown')}
- **Resource**: {finding.get('resource', 'unknown')}
- **Title**: {finding.get('title', 'N/A')}
- **Detail**: {finding.get('detail', 'N/A')}
- **Current Remediation**: {finding.get('remediation', 'N/A')}

Provide a comprehensive remediation guide with the following sections:

## 1. Threat Model & Impact
Explain why this finding matters, the attack vectors it enables, and potential business impact.

## 2. Root Cause Analysis
Identify the specific misconfiguration or security gap.

## 3. Step-by-Step Remediation
Provide exact CLI commands for {finding.get('cloud', 'the relevant cloud provider').upper()} to fix this issue.
Include prerequisites and any necessary backups.

## 4. Verification Steps
Commands to verify the fix was applied correctly.

## 5. Rollback Plan
Steps to revert if the remediation causes issues.

## 6. Prevention & Monitoring
How to detect regression and prevent similar issues (IaC policies, monitoring alerts, etc.).

## 7. References
Relevant CWE IDs, cloud provider security best practices, or compliance framework mappings (CIS, NIST, etc.).

Be specific with command syntax. Mark any advisory vs. mandatory steps.
"""

    def _fallback_remediation(self, finding: dict) -> str:
        """Provide a basic remediation guide when AI is unavailable."""
        cloud = finding.get("cloud", "unknown").upper()
        return f"""## AI Analysis Unavailable (Demo Mode)

This finding requires manual review. Below is the built-in remediation guidance:

### Threat Model & Impact
{finding.get('detail', 'No detail available')}

### Root Cause Analysis
{finding.get('title', 'No title available')}

### Step-by-Step Remediation ({cloud})
{finding.get('remediation', 'No remediation provided')}

### Verification Steps
Re-run the security scan to confirm the finding is resolved.

### Prevention & Monitoring
- Enable continuous scanning in CI/CD pipeline
- Implement Infrastructure-as-Code policy checks (e.g., Checkov, tfsec)
- Configure cloud provider security hub/guardduty alerts

### References
- Cloud provider security best practices
- CIS Benchmarks for {cloud}
- NIST Cybersecurity Framework
"""
    async def generate_executive_summary(self, scan_data: dict) -> str:
        """Generate AI-powered executive summary for a scan."""
        if not self.is_configured():
            return self._fallback_executive_summary(scan_data)

        system_prompt = (
            "You are a cloud security executive advisor. "
            "Provide concise, risk-focused executive summaries of security scan results. "
            "Format as markdown with clear sections. "
            "Include a risk rating (Critical/High/Medium/Low) and top 3 prioritized actions."
        )

        prompt = self._build_executive_summary_prompt(scan_data)

        try:
            response = await self._provider.generate(prompt, system=system_prompt, temperature=0.2, max_tokens=3000)
            return response.content
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.json().get("error", {}).get("message", str(e))
            except Exception:
                error_detail = str(e)
            return f"**AI Analysis Unavailable** (Provider error: {error_detail})\n\n{self._fallback_executive_summary(scan_data)}"
        except Exception as e:
            return f"**AI Analysis Unavailable** ({type(e).__name__}: {str(e)})\n\n{self._fallback_executive_summary(scan_data)}"

    def _build_executive_summary_prompt(self, scan: dict) -> str:
        """Build a detailed prompt for executive summary generation."""
        findings = scan.get("findings", [])
        severity_counts = scan.get("severity_counts", {})
        by_category = scan.get("by_category", {})
        by_cloud = scan.get("by_cloud", {})

        # Get top findings by severity score
        top_findings = sorted(findings, key=lambda f: f.get("score", 0), reverse=True)[:10]
        top_findings_str = "\n".join([
            f"- [{f.get('severity', 'info').upper()}] {f.get('title', 'N/A')} ({f.get('resource', 'N/A')}) - Score: {f.get('score', 0):.1f}"
            for f in top_findings
        ])

        return f"""
Scan Overview:
- **Cloud Provider**: {scan.get('cloud', 'unknown').upper()}
- **Region**: {scan.get('region', 'N/A')}
- **Category**: {scan.get('category', 'All')}
- **Scan Time**: {scan.get('started_at', 'N/A')}
- **Total Findings**: {scan.get('findings_count', 0)}
- **Critical**: {severity_counts.get('critical', 0)} | **High**: {severity_counts.get('high', 0)} | **Medium**: {severity_counts.get('medium', 0)} | **Low**: {severity_counts.get('low', 0)} | **Info**: {severity_counts.get('info', 0)}
- **By Category**: {by_category}
- **By Cloud**: {by_cloud}

Top Findings by Risk Score:
{top_findings_str}

Provide an executive security summary with the following sections:

## 1. Risk Rating
Assign an overall risk rating: **Critical / High / Medium / Low** with brief justification.

## 2. Key Findings Summary
Brief narrative (2-3 sentences) summarizing the security posture.

## 3. Top 3 Priority Actions
List exactly 3 concrete, prioritized actions with:
- Action description
- Affected resources
- Estimated effort (Low/Medium/High)
- Cloud CLI command or console path

## 4. Compliance & Framework Gaps
Note any CIS, NIST, or regulatory compliance implications.

## 5. Strategic Recommendations
2-3 longer-term strategic improvements (IaC policy, guardrails, architecture changes).

Be concise, executive-focused, and action-oriented. Use markdown formatting.
"""

    def _fallback_executive_summary(self, scan: dict) -> str:
        """Provide a basic executive summary when AI is unavailable."""
        findings_count = scan.get("findings_count", 0)
        critical = scan.get("severity_counts", {}).get("critical", 0)
        high = scan.get("severity_counts", {}).get("high", 0)
        cloud = scan.get("cloud", "unknown").upper()

        # Determine risk rating
        if critical > 0:
            risk_rating = "Critical"
        elif high > 0:
            risk_rating = "High"
        elif findings_count > 0:
            risk_rating = "Medium"
        else:
            risk_rating = "Low"

        return f"""## AI Executive Summary Unavailable (Demo Mode)

### Risk Rating: {risk_rating}
Based on {findings_count} findings ({critical} critical, {high} high) in {cloud} scan.

### Key Findings Summary
This {cloud} security scan detected {findings_count} security findings across storage, IAM, network, and logging configurations. Immediate attention required for critical and high-severity issues.

### Top 3 Priority Actions
1. **Remediate critical findings** — Address {critical} critical-severity misconfigurations immediately
   - Affected: See findings list
   - Effort: High
   - Command: Re-run scan with specific category to identify exact resources

2. **Review high-severity findings** — Evaluate and remediate {high} high-severity issues
   - Affected: See findings list
   - Effort: Medium
   - Command: Review finding details for specific remediation steps

3. **Enable continuous scanning** — Integrate automated scans into CI/CD pipeline
   - Affected: All cloud resources
   - Effort: Low
   - Command: Configure scheduled scans via API

### Compliance & Framework Gaps
- CIS Benchmarks: Findings may indicate gaps in CIS {cloud} Foundations
- NIST CSF: Identify, Protect, and Detect functions need strengthening

### Strategic Recommendations
- Implement Infrastructure-as-Code policy enforcement (Checkov, tfsec, OPA)
- Enable cloud provider native security services (Security Hub, Security Command Center, Defender for Cloud)
- Establish security baseline and drift detection for all environments
"""


# Singleton instance
llm_service = LLMService()
