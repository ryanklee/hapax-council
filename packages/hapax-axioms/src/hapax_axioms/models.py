"""Pydantic models for axiom and pattern bundles.

Mirrors the schema of `axioms/registry.yaml` and the T0 patterns from
`hooks/scripts/axiom-patterns.sh` in the upstream constitution and council
repos. Models validate the bundled YAML at load time and are also the
public API for projects that want to author their own axiom bundles.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Tier = Literal["T0", "T1", "T2", "T3"]
AxiomScope = Literal["constitutional", "domain"]
AxiomType = Literal["hardcoded", "softcoded"]
AxiomStatus = Literal["active", "retired"]


class Implication(BaseModel):
    """A derived implication of an axiom (e.g. su-auth-001)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str = Field(..., description="Stable implication ID, e.g. 'su-auth-001'.")
    tier: Tier = Field("T2", description="Enforcement tier: T0 block, T1 review, T2 warn, T3 lint.")
    text: str = Field(..., description="Human-readable implication statement.")
    enforcement: str = Field(
        "review",
        description="Enforcement mode: 'block', 'review', 'warn', 'lint'.",
    )
    canon: str | None = Field(None, description="Interpretive canon (textualist/purposivist/etc).")
    mode: str | None = Field(None, description="Compatibility / sufficiency / etc.")
    level: str | None = Field(None, description="Granularity level (component/subsystem/system).")


class Axiom(BaseModel):
    """A single axiom from the constitutional substrate.

    Mirrors `axioms/registry.yaml` entries in hapax-constitution.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str = Field(..., description="Stable axiom ID, e.g. 'single_user'.")
    text: str = Field(..., description="Canonical axiom statement.")
    weight: int = Field(..., ge=0, le=100, description="0-100. Higher wins on conflict.")
    type: AxiomType = Field(..., description="hardcoded (immutable) or softcoded (interpretable).")
    created: str = Field(..., description="ISO date the axiom was published.")
    status: AxiomStatus = Field("active", description="active or retired.")
    supersedes: str | None = Field(None, description="ID of axiom this one supersedes.")
    scope: AxiomScope = Field(
        "constitutional",
        description="constitutional (always-on) or domain (scoped).",
    )
    domain: str | None = Field(None, description="Domain key when scope=domain (e.g. management).")


class AxiomBundle(BaseModel):
    """Top-level structure of the bundled axioms YAML."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    schema_version: str = Field(..., description="SchemaVer of this bundle.")
    source_repo: str = Field(..., description="Canonical upstream repo URL.")
    source_path: str | None = Field(None, description="Path within the upstream repo.")
    snapshot_date: str = Field(..., description="ISO date this snapshot was taken.")
    axioms: list[Axiom] = Field(default_factory=list)


class Pattern(BaseModel):
    """A single regex pattern that detects an axiom-violating construct.

    Patterns are compiled with case-insensitive matching by `scan_text`.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str = Field(..., description="Stable pattern ID, e.g. 'su-auth-class-user-manager'.")
    axiom_id: str = Field(..., description="Axiom this pattern enforces.")
    implication_id: str = Field(..., description="Implication this pattern derives from.")
    tier: Tier = Field("T0", description="Enforcement tier.")
    regex: str = Field(..., description="Python re-compatible regex.")
    description: str = Field(..., description="What the pattern catches and why.")
    false_positive_notes: str | None = Field(None, description="Known false-positive cases.")


class PatternBundle(BaseModel):
    """Top-level structure of the bundled patterns YAML."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    schema_version: str = Field(..., description="SchemaVer of this bundle.")
    source_repo: str = Field(..., description="Canonical upstream repo URL.")
    snapshot_date: str = Field(..., description="ISO date this snapshot was taken.")
    patterns: list[Pattern] = Field(default_factory=list)
