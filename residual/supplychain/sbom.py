"""SBOM generation and vulnerability scanning. Implements ENT5-R2 and ENT5-R3.

ENT5-R2: a Software Bill of Materials (CycloneDX JSON) is generated
automatically during the build, listing every direct and transitive
dependency, every version, and every license.

ENT5-R3: the SBOM MUST be scanned for known vulnerabilities before
every release; HIGH/CRITICAL findings MUST be fixed or explicitly
accepted with justification, and scan results published.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol

from residual.core import ContractError, canonical, digest

CYCLONEDX_SPEC_VERSION = "1.5"
BLOCKING_SEVERITIES = frozenset({"HIGH", "CRITICAL"})
VALID_SEVERITIES = frozenset({"NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"})


@dataclass(frozen=True)
class Dependency:
    """A single SBOM component. Implements ENT5-R2."""

    name: str
    version: str
    license: str
    transitive: bool = False
    purl: str | None = None

    def __post_init__(self):
        for field_name in ("name", "version", "license"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ContractError(f"dependency {field_name} required")
        if type(self.transitive) is not bool:
            raise ContractError("transitive flag must be bool")
        if self.purl is not None and not isinstance(self.purl, str):
            raise ContractError("purl must be a string or None")


@dataclass(frozen=True)
class SBOM:
    """A CycloneDX SBOM for a release. Implements ENT5-R2."""

    release_version: str
    components: tuple[Dependency, ...]

    def __post_init__(self):
        if not isinstance(self.release_version, str) or not self.release_version:
            raise ContractError("release_version required")
        for component in self.components:
            if not isinstance(component, Dependency):
                raise ContractError("components must be Dependency instances")

    @property
    def sha256(self) -> str:
        return digest(self.to_cyclonedx())

    def to_cyclonedx(self) -> dict:
        """Serialize as CycloneDX JSON. Implements ENT5-R2."""
        components = []
        for dep in sorted(self.components, key=lambda d: (d.name, d.version)):
            entry = {
                "type": "library",
                "name": dep.name,
                "version": dep.version,
                "licenses": [{"license": {"name": dep.license}}],
                "scope": "excluded" if dep.transitive else "required",
                "properties": [
                    {"name": "residual:transitive", "value": str(dep.transitive).lower()}
                ],
            }
            if dep.purl:
                entry["purl"] = dep.purl
            components.append(entry)
        return {
            "bomFormat": "CycloneDX",
            "specVersion": CYCLONEDX_SPEC_VERSION,
            "version": 1,
            "metadata": {
                "component": {
                    "type": "application",
                    "name": "residual",
                    "version": self.release_version,
                }
            },
            "components": components,
        }


def generate_sbom(
    release_version: str,
    dependencies: Iterable[Dependency],
) -> SBOM:
    """Generate an SBOM during the build. Implements ENT5-R2.

    Every direct dependency, every transitive dependency, every
    version, and every license MUST be listed; duplicates are an error.
    """
    deps = tuple(dependencies)
    seen: set[tuple[str, str]] = set()
    for dep in deps:
        if not isinstance(dep, Dependency):
            raise ContractError("dependencies must be Dependency instances")
        key = (dep.name, dep.version)
        if key in seen:
            raise ContractError(f"duplicate dependency {dep.name}@{dep.version}")
        seen.add(key)
    return SBOM(release_version=release_version, components=deps)


@dataclass(frozen=True)
class Vulnerability:
    """A known vulnerability affecting a dependency. Implements ENT5-R3."""

    cve_id: str
    package: str
    severity: str
    affected_versions: tuple[str, ...]
    fixed_version: str | None = None

    def __post_init__(self):
        if not isinstance(self.cve_id, str) or not self.cve_id.startswith("CVE-"):
            raise ContractError("cve_id must look like CVE-YYYY-NNNN")
        if not isinstance(self.package, str) or not self.package:
            raise ContractError("vulnerability package required")
        if self.severity not in VALID_SEVERITIES:
            raise ContractError(f"severity must be one of {sorted(VALID_SEVERITIES)}")
        if not self.affected_versions:
            raise ContractError("affected_versions must be nonempty")

    def affects(self, name: str, version: str) -> bool:
        return self.package == name and version in self.affected_versions


class VulnerabilityDatabase(Protocol):
    """Offline CVE database interface. Implements ENT5-R3.

    Production implementations load a mirrored CVE feed; tests use an
    in-memory fixture. Lookups MUST NOT require network access.
    """

    def vulnerabilities_for(self, package: str, version: str) -> list[Vulnerability]:
        """Return known vulnerabilities for package@version. Implements ENT5-R3."""
        ...


@dataclass(frozen=True)
class FixtureVulnerabilityDatabase:
    """In-memory offline CVE database fixture. Implements ENT5-R3."""

    entries: tuple[Vulnerability, ...] = ()

    def vulnerabilities_for(self, package: str, version: str) -> list[Vulnerability]:
        return [v for v in self.entries if v.affects(package, version)]


@dataclass(frozen=True)
class ScanFinding:
    """One vulnerability matched against one component. Implements ENT5-R3."""

    vulnerability: Vulnerability
    dependency: Dependency
    accepted: bool = False
    justification: str = ""

    def accepted_record(self, justification: str) -> "ScanFinding":
        """Explicitly accept this finding with justification. Implements ENT5-R3."""
        if not isinstance(justification, str) or not justification.strip():
            raise ContractError("ENT5-R3: acceptance requires explicit justification")
        return ScanFinding(
            vulnerability=self.vulnerability,
            dependency=self.dependency,
            accepted=True,
            justification=justification,
        )


@dataclass(frozen=True)
class ScanResult:
    """Published result of scanning an SBOM. Implements ENT5-R3."""

    sbom_sha256: str
    findings: tuple[ScanFinding, ...]

    @property
    def blocking_findings(self) -> list[ScanFinding]:
        """Unaccepted HIGH/CRITICAL findings that block release. Implements ENT5-R3."""
        return [
            f
            for f in self.findings
            if f.vulnerability.severity in BLOCKING_SEVERITIES and not f.accepted
        ]

    @property
    def release_allowed(self) -> bool:
        """HIGH/CRITICAL MUST be fixed or explicitly accepted. Implements ENT5-R3."""
        return not self.blocking_findings

    def to_dict(self) -> dict:
        """Published scan report. Implements ENT5-R3."""
        return {
            "sbom_sha256": self.sbom_sha256,
            "release_allowed": self.release_allowed,
            "findings": [
                {
                    "cve_id": f.vulnerability.cve_id,
                    "package": f.dependency.name,
                    "version": f.dependency.version,
                    "severity": f.vulnerability.severity,
                    "accepted": f.accepted,
                    "justification": f.justification,
                }
                for f in self.findings
            ],
        }


def scan_sbom(sbom: SBOM, database: VulnerabilityDatabase) -> ScanResult:
    """Scan an SBOM against an offline CVE database. Implements ENT5-R3."""
    if not isinstance(sbom, SBOM):
        raise ContractError("sbom must be an SBOM")
    findings: list[ScanFinding] = []
    for dep in sbom.components:
        for vuln in database.vulnerabilities_for(dep.name, dep.version):
            findings.append(ScanFinding(vulnerability=vuln, dependency=dep))
    findings.sort(key=lambda f: (f.vulnerability.cve_id, f.dependency.name))
    return ScanResult(sbom_sha256=sbom.sha256, findings=tuple(findings))
