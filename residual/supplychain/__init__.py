"""Supply chain security (SPEC-ENT-005).

Implements ENT5-R1 through ENT5-R8: signed releases, SBOM,
vulnerability scanning, third-party audit tracking, vulnerability
disclosure SLAs, dependency pinning, module sandboxing, and
reproducible build verification.
"""
from residual.supplychain.signing import (
    BuildManifest,
    HSMSigner,
    SoftwareTestSigner,
    SignedRelease,
    sign_release,
    verify_release,
)
from residual.supplychain.sbom import (
    Dependency,
    SBOM,
    generate_sbom,
    Vulnerability,
    VulnerabilityDatabase,
    FixtureVulnerabilityDatabase,
    ScanFinding,
    ScanResult,
    scan_sbom,
)
from residual.supplychain.audit import (
    AuditScope,
    ThirdPartyAudit,
    AuditTracker,
)
from residual.supplychain.disclosure import (
    Severity,
    DisclosureReport,
    DisclosureTracker,
)
from residual.supplychain.pinning import (
    PinnedDependency,
    parse_pins,
    verify_pin,
    verify_all,
)
from residual.supplychain.sandbox import (
    SandboxPolicy,
    ModuleManifest,
    validate_manifest,
    run_sandboxed,
)
from residual.supplychain.reproducible import (
    ReproducibilityReport,
    verify_reproducible,
)

__all__ = [name for name in dir() if not name.startswith("_")]
