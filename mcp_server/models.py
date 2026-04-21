"""
Pydantic models for the Toolbank Record schema and related structures.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class SourceType(str, Enum):
    openapi = "openapi"
    docs = "docs"
    github = "github"
    mcp_server = "mcp_server"
    sdk = "sdk"
    cli = "cli"


class Transport(str, Enum):
    rest = "rest"
    graphql = "graphql"
    cli = "cli"
    python = "python"
    node = "node"
    webhook = "webhook"
    local = "local"


class AuthType(str, Enum):
    api_key = "api_key"
    oauth = "oauth"
    none = "none"
    env_var = "env_var"


class SideEffectLevel(str, Enum):
    read = "read"
    write = "write"
    destructive = "destructive"


class PermissionPolicy(str, Enum):
    auto = "auto"
    confirm = "confirm"
    deny = "deny"


class ToolStatus(str, Enum):
    draft = "draft"
    verified = "verified"
    approved = "approved"
    deprecated = "deprecated"


class AdapterKind(str, Enum):
    http = "http"
    subprocess = "subprocess"
    python_func = "python_func"
    graphql = "graphql"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class AuthInfo(BaseModel):
    type: AuthType = AuthType.none
    required_env: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)


class ToolExample(BaseModel):
    goal: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    expected_output: dict[str, Any] | None = None


class HttpAdapter(BaseModel):
    kind: AdapterKind = AdapterKind.http
    method: str = "GET"
    url_template: str
    headers: dict[str, str] = Field(default_factory=dict)
    body_template: dict[str, Any] | None = None


class SubprocessAdapter(BaseModel):
    kind: AdapterKind = AdapterKind.subprocess
    command: str
    args_template: list[str] = Field(default_factory=list)
    sandbox: bool = True
    timeout_seconds: int = 30


class ExecutionAdapter(BaseModel):
    kind: AdapterKind = AdapterKind.http
    method: str | None = None
    url_template: str | None = None
    command: str | None = None
    args_template: list[str] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)
    sandbox: bool = False
    timeout_seconds: int = 30


# ---------------------------------------------------------------------------
# Tool DNA Fingerprint
# ---------------------------------------------------------------------------

class ToolDNA(BaseModel):
    """Semantic fingerprint for deduplication across differently-named tools."""

    intent: str = ""
    domain: str = ""
    action: str = ""
    object: str = ""
    input_signature: list[str] = Field(default_factory=list)
    auth_signature: str = ""
    side_effect: SideEffectLevel = SideEffectLevel.read
    transport_signature: str = ""

    def fingerprint(self) -> str:
        canonical = json.dumps(self.model_dump(), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Main Toolbank Record
# ---------------------------------------------------------------------------

class ToolbankRecord(BaseModel):
    """
    Canonical record for a single discovered tool / API capability.
    Every record produced by the harvester must conform to this schema.
    """

    id: str
    name: str
    namespace: str
    description: str

    source_urls: list[str] = Field(default_factory=list)
    source_type: SourceType = SourceType.docs
    transport: Transport = Transport.rest

    auth: AuthInfo = Field(default_factory=AuthInfo)

    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)

    examples: list[ToolExample] = Field(default_factory=list)

    side_effect_level: SideEffectLevel = SideEffectLevel.read
    permission_policy: PermissionPolicy = PermissionPolicy.auto

    rate_limit_notes: str = ""
    pricing_notes: str = ""
    install_notes: str = ""

    execution_adapter: ExecutionAdapter | None = None

    tags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    version_hash: str = ""
    status: ToolStatus = ToolStatus.draft

    dna: ToolDNA = Field(default_factory=ToolDNA)

    @model_validator(mode="after")
    def set_defaults(self) -> "ToolbankRecord":
        if not self.id:
            self.id = f"{self.namespace}.{self.name}"
        if not self.version_hash:
            canonical = json.dumps(
                {"input_schema": self.input_schema, "description": self.description},
                sort_keys=True,
            )
            self.version_hash = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
        # Auto-assign permission policy based on side effect level
        if self.permission_policy == PermissionPolicy.auto:
            if self.side_effect_level == SideEffectLevel.write:
                self.permission_policy = PermissionPolicy.confirm
            elif self.side_effect_level == SideEffectLevel.destructive:
                self.permission_policy = PermissionPolicy.deny
        return self


# ---------------------------------------------------------------------------
# Extraction Result (LLM output wrapper)
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    field: str
    source_url: str
    quote: str


class ExtractionResult(BaseModel):
    """
    Wrapper produced by extractors (especially LLM-based ones).
    The record itself is not trusted unless confidence is high enough.
    """

    record: dict[str, Any]
    evidence: list[EvidenceItem] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_url: str = ""
    extractor: str = ""


# ---------------------------------------------------------------------------
# Gap Mining Record
# ---------------------------------------------------------------------------

class FailedQuery(BaseModel):
    user_goal: str
    failed_query: str
    tools_returned: list[str] = Field(default_factory=list)
    timestamp: str = ""


# ---------------------------------------------------------------------------
# Verification Result
# ---------------------------------------------------------------------------

class VerificationResult(BaseModel):
    record_id: str
    schema_valid: bool = False
    examples_valid: bool = False
    safety_checked: bool = False
    drift_detected: bool = False
    issues: list[str] = Field(default_factory=list)
    passed: bool = False

    @model_validator(mode="after")
    def compute_passed(self) -> "VerificationResult":
        self.passed = self.schema_valid and not self.drift_detected and len(self.issues) == 0
        return self
