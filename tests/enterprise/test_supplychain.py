"""Tests for SPEC-ENT-005 (ENT5-R1 through ENT5-R8)."""
from __future__ import annotations

import hashlib
import os
import sys

import pytest

from residual.core import ContractError
from residual.supplychain import (
    AuditTracker,
    BuildManifest,
    Dependency,
    DisclosureReport,
    DisclosureTracker,
    FixtureVulnerabilityDatabase,
    ModuleManifest,
    SBOM,
    SandboxPolicy,
    Severity,
    SoftwareTestSigner,
    ThirdPartyAudit,
    Vulnerability,
    generate_sbom,
    parse_pins,
    run_sandboxed,
    scan_sbom,
    sign_release,
    validate_manifest,
    verify_all,
    verify_pin,
    verify_release,
    verify_reproducible,
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- ENT5-R1


class TestSigning:
    def test_sign_and_verify_release(self):
        signer = SoftwareTestSigner()
        digest = sha(b"artifact-bytes")
        release = sign_release(digest, signer, allow_software=True)
        assert release.key_id == signer.key_id
        assert verify_release(release, signer)

    def test_signature_covers_artifact(self):
        signer = SoftwareTestSigner()
        release = sign_release(sha(b"a"), signer, allow_software=True)
        tampered = sign_release(sha(b"b"), signer, allow_software=True)
        # Signature for artifact "b" must not verify against artifact "a" payload.
        from residual.supplychain.signing import SignedRelease

        mixed = SignedRelease(
            artifact_sha256=sha(b"a"),
            signature=tampered.signature,
            key_id=signer.key_id,
            hardware=False,
        )
        assert not verify_release(mixed, signer)

    def test_hardware_key_required(self):
        signer = SoftwareTestSigner()
        with pytest.raises(ContractError, match="hardware"):
            sign_release(sha(b"x"), signer)

    def test_signature_covers_manifest(self):
        signer = SoftwareTestSigner()
        manifest = BuildManifest(
            version="1.0.0",
            inputs={"src/main.py": sha(b"src")},
            outputs={"dist/residual.whl": sha(b"out")},
        )
        release = sign_release(sha(b"out"), signer, manifest=manifest, allow_software=True)
        assert verify_release(release, signer)
        other = BuildManifest(version="1.0.0", inputs=manifest.inputs, outputs=manifest.outputs)
        assert other.sha256 == manifest.sha256

    def test_manifest_rejects_bad_hash(self):
        with pytest.raises(ContractError):
            BuildManifest(version="1", inputs={"a": "not-a-hash"}, outputs={})


# ---------------------------------------------------------------- ENT5-R2


class TestSBOM:
    def deps(self):
        return [
            Dependency(name="requests", version="2.31.0", license="Apache-2.0"),
            Dependency(name="urllib3", version="2.2.1", license="MIT", transitive=True),
        ]

    def test_generates_cyclonedx(self):
        sbom = generate_sbom("1.0.0", self.deps())
        doc = sbom.to_cyclonedx()
        assert doc["bomFormat"] == "CycloneDX"
        assert doc["metadata"]["component"]["name"] == "residual"
        names = {c["name"] for c in doc["components"]}
        assert names == {"requests", "urllib3"}

    def test_lists_direct_transitive_versions_licenses(self):
        sbom = generate_sbom("1.0.0", self.deps())
        doc = sbom.to_cyclonedx()
        by_name = {c["name"]: c for c in doc["components"]}
        assert by_name["requests"]["scope"] == "required"
        assert by_name["urllib3"]["scope"] == "excluded"
        assert by_name["requests"]["version"] == "2.31.0"
        assert by_name["urllib3"]["licenses"][0]["license"]["name"] == "MIT"

    def test_duplicate_dependency_rejected(self):
        with pytest.raises(ContractError):
            generate_sbom(
                "1.0.0",
                [
                    Dependency(name="a", version="1", license="MIT"),
                    Dependency(name="a", version="1", license="MIT"),
                ],
            )

    def test_sbom_deterministic(self):
        a = generate_sbom("1.0.0", self.deps())
        b = generate_sbom("1.0.0", list(reversed(self.deps())))
        assert a.sha256 == b.sha256


# ---------------------------------------------------------------- ENT5-R3


class TestVulnerabilityScan:
    def setup_method(self):
        self.critical = Vulnerability(
            cve_id="CVE-2024-0001",
            package="requests",
            severity="CRITICAL",
            affected_versions=("2.31.0",),
            fixed_version="2.32.0",
        )
        self.low = Vulnerability(
            cve_id="CVE-2024-0002",
            package="urllib3",
            severity="LOW",
            affected_versions=("2.2.1",),
        )
        self.db = FixtureVulnerabilityDatabase(entries=(self.critical, self.low))
        self.sbom = generate_sbom(
            "1.0.0",
            [
                Dependency(name="requests", version="2.31.0", license="Apache-2.0"),
                Dependency(name="urllib3", version="2.2.1", license="MIT", transitive=True),
            ],
        )

    def test_scan_finds_vulnerabilities(self):
        result = scan_sbom(self.sbom, self.db)
        assert len(result.findings) == 2
        assert result.sbom_sha256 == self.sbom.sha256

    def test_unaccepted_critical_blocks_release(self):
        result = scan_sbom(self.sbom, self.db)
        assert not result.release_allowed
        assert [f.vulnerability.cve_id for f in result.blocking_findings] == ["CVE-2024-0001"]

    def test_accepted_with_justification_allows_release(self):
        result = scan_sbom(self.sbom, self.db)
        findings = tuple(
            f.accepted_record("not exploitable: feature unused")
            if f.vulnerability.severity == "CRITICAL"
            else f
            for f in result.findings
        )
        from residual.supplychain.sbom import ScanResult

        accepted = ScanResult(sbom_sha256=result.sbom_sha256, findings=findings)
        assert accepted.release_allowed

    def test_acceptance_requires_justification(self):
        result = scan_sbom(self.sbom, self.db)
        with pytest.raises(ContractError):
            result.findings[0].accepted_record("  ")

    def test_fixed_version_unaffected(self):
        sbom = generate_sbom(
            "1.0.0", [Dependency(name="requests", version="2.32.0", license="Apache-2.0")]
        )
        result = scan_sbom(sbom, self.db)
        assert result.release_allowed
        assert result.to_dict()["findings"] == []


# ---------------------------------------------------------------- ENT5-R4


class TestAudit:
    def audit(self, day=100, firm="Trail of Bits", published=True):
        return ThirdPartyAudit(
            firm=firm,
            completed_day=day,
            scopes=frozenset(
                {"code_review", "penetration_testing", "architecture_review", "compliance_verification"}
            ),
            published=published,
            report_url="https://example.com/audit.pdf",
        )

    def test_recognized_firms(self):
        for firm in ("NCC Group", "Trail of Bits", "Cure53"):
            assert ThirdPartyAudit(
                firm=firm, completed_day=1, scopes=self.audit().scopes, published=True
            ).firm_recognized

    def test_unrecognized_firm_requires_equivalence(self):
        with pytest.raises(ContractError):
            self.audit(firm="Some Shop")
        # With documented equivalence it is accepted:
        assert ThirdPartyAudit(
            firm="Some Shop",
            completed_day=1,
            scopes=self.audit().scopes,
            published=True,
            recognized_equivalent="ISO 17025-accredited security lab",
        ).firm == "Some Shop"

    def test_incomplete_scope_rejected(self):
        with pytest.raises(ContractError, match="scope"):
            ThirdPartyAudit(
                firm="Cure53",
                completed_day=1,
                scopes=frozenset({"code_review"}),
                published=True,
            )

    def test_annual_cadence(self):
        tracker = AuditTracker()
        assert not tracker.is_current(10)
        tracker.record(self.audit(day=100))
        assert tracker.is_current(100)
        assert tracker.is_current(465)
        assert not tracker.is_current(466)
        assert tracker.next_due_day(100) == 465

    def test_results_must_be_publishable_tracking(self):
        tracker = AuditTracker()
        tracker.record(self.audit(published=False))
        assert len(tracker.unpublished()) == 1

    def test_duplicate_record_rejected(self):
        tracker = AuditTracker()
        tracker.record(self.audit())
        with pytest.raises(ContractError):
            tracker.record(self.audit())


# ---------------------------------------------------------------- ENT5-R5


class TestDisclosure:
    def report(self, rid="R-1", severity=Severity.CRITICAL):
        return DisclosureReport(
            report_id=rid, severity=severity, summary="xss in tui", reporter="researcher@x.io"
        )

    def test_ack_within_72h(self):
        tracker = DisclosureTracker()
        tracker.receive(self.report(), hour=0)
        tracker.acknowledge("R-1", hour=72)
        assert tracker.ack_sla_met("R-1")

    def test_ack_after_72h_fails_sla(self):
        tracker = DisclosureTracker()
        tracker.receive(self.report(), hour=0)
        tracker.acknowledge("R-1", hour=73)
        assert not tracker.ack_sla_met("R-1")

    def test_critical_patch_within_14_days(self):
        tracker = DisclosureTracker()
        tracker.receive(self.report(), hour=0)
        tracker.mark_patched("R-1", hour=336)
        assert tracker.patch_sla_met("R-1")
        tracker2 = DisclosureTracker()
        tracker2.receive(self.report(), hour=0)
        tracker2.mark_patched("R-1", hour=337)
        assert not tracker2.patch_sla_met("R-1")

    def test_non_critical_has_no_14_day_clock(self):
        tracker = DisclosureTracker()
        tracker.receive(self.report(severity=Severity.LOW), hour=0)
        tracker.mark_patched("R-1", hour=9999)
        assert tracker.patch_sla_met("R-1")

    def test_overdue_detection(self):
        tracker = DisclosureTracker()
        tracker.receive(self.report(), hour=0)
        tracker.receive(self.report(rid="R-2", severity=Severity.HIGH), hour=10)
        assert tracker.overdue_acknowledgements(100) == ["R-1", "R-2"]
        assert tracker.overdue_critical_patches(400) == ["R-1"]
        tracker.acknowledge("R-1", hour=10)
        assert tracker.overdue_acknowledgements(100) == ["R-2"]

    def test_compliance_report(self):
        tracker = DisclosureTracker()
        tracker.receive(self.report(), hour=0)
        tracker.acknowledge("R-1", hour=24)
        tracker.mark_patched("R-1", hour=100)
        report = tracker.compliance_report(current_hour=200)
        assert report["total_reports"] == 1
        assert report["ack_sla_met"]["R-1"] is True
        assert report["patch_sla_met"]["R-1"] is True
        assert report["overdue_acknowledgements"] == []

    def test_double_ack_rejected(self):
        tracker = DisclosureTracker()
        tracker.receive(self.report(), hour=0)
        tracker.acknowledge("R-1", hour=1)
        with pytest.raises(ContractError):
            tracker.acknowledge("R-1", hour=2)


# ---------------------------------------------------------------- ENT5-R6


class TestPinning:
    def test_parse_valid_pins(self):
        pins = parse_pins(
            f"requests==2.31.0 --hash=sha256:{sha(b'req')}\n"
            f"# comment\n\n"
            f"urllib3==2.2.1 --hash=sha256:{sha(b'url')}\n"
        )
        assert [p.name for p in pins] == ["requests", "urllib3"]
        assert pins[0].version == "2.31.0"

    @pytest.mark.parametrize("line", ["requests>=2.0", "requests~=2.0", "requests<3", "requests"])
    def test_floating_versions_rejected(self, line):
        with pytest.raises(ContractError):
            parse_pins(line + "\n")

    def test_missing_hash_rejected(self):
        with pytest.raises(ContractError, match="--hash"):
            parse_pins("requests==2.31.0\n")

    def test_duplicate_pin_rejected(self):
        with pytest.raises(ContractError):
            parse_pins(
                f"a==1 --hash=sha256:{sha(b'1')}\na==2 --hash=sha256:{sha(b'2')}\n"
            )

    def test_hash_verified_on_install(self):
        pins = parse_pins(f"requests==2.31.0 --hash=sha256:{sha(b'artifact')}\n")
        verify_pin(pins[0], b"artifact")
        with pytest.raises(ContractError, match="hash mismatch"):
            verify_pin(pins[0], b"tampered")

    def test_verify_all(self):
        pins = parse_pins(
            f"a==1 --hash=sha256:{sha(b'A')}\nb==2 --hash=sha256:{sha(b'B')}\n"
        )
        verify_all(pins, {"a": b"A", "b": b"B"})
        with pytest.raises(ContractError):
            verify_all(pins, {"a": b"A"})
        with pytest.raises(ContractError):
            verify_all(pins, {"a": b"A", "b": b"B", "c": b"C"})


# ---------------------------------------------------------------- ENT5-R7


class TestSandbox:
    def setup_method(self):
        if sys.platform != "linux":
            pytest.skip("ENT5-R7 kernel sandbox requires Linux")
        if os.geteuid() == 0:
            pytest.skip("ENT5-R7 intentionally refuses a root parent")

    def manifest(self, **policy_kwargs):
        return ModuleManifest(
            name="thirdparty.demo",
            version="1.0.0",
            policy=SandboxPolicy(**policy_kwargs),
        )

    def test_default_policy_is_isolated(self):
        policy = SandboxPolicy()
        assert policy.allow_network is False
        assert policy.run_as_root is False
        assert policy.filesystem_allowlist == ()
        assert policy.max_memory_mb > 0 and policy.max_cpu_seconds > 0

    def test_root_rejected(self):
        with pytest.raises(ContractError):
            SandboxPolicy(run_as_root=True)
        with pytest.raises(ContractError):
            SandboxPolicy(run_as_user="root")

    def test_network_manifest_rejected(self):
        manifest = self.manifest(allow_network=True)
        with pytest.raises(ContractError, match="network"):
            validate_manifest(manifest)

    def test_network_egress_denied_by_kernel(self):
        source = (
            "def go():\n"
            "    import socket\n"
            "    socket.create_connection(('203.0.113.1', 9), timeout=0.2)\n"
            "    return 1\n"
        )
        with pytest.raises(ContractError, match="sandboxed module failed"):
            run_sandboxed(self.manifest(), source, "go")

    def test_filesystem_outside_allowlist_denied(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        source = "def go():\n    return open('/etc/passwd').read()\n"
        manifest = self.manifest(filesystem_allowlist=(str(data.resolve()),))
        with pytest.raises(ContractError, match="sandboxed module failed"):
            run_sandboxed(manifest, source, "go")

    def test_filesystem_allowlist_permitted(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        config = data / "config.txt"
        config.write_text("hello", encoding="utf-8")
        source = f"def go():\n    return open({str(config.resolve())!r}).read()\n"
        manifest = self.manifest(filesystem_allowlist=(str(data.resolve()),))
        assert run_sandboxed(manifest, source, "go") == "hello"

    def test_path_traversal_denied(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        secret = tmp_path / "secret"
        secret.write_text("nope", encoding="utf-8")
        escaped = str(data.resolve()) + "/../secret"
        source = f"def go():\n    return open({escaped!r}).read()\n"
        manifest = self.manifest(filesystem_allowlist=(str(data.resolve()),))
        with pytest.raises(ContractError, match="containment"):
            run_sandboxed(manifest, source, "go")

    def test_write_denied(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        target = data / "x"
        source = f"def go():\n    open({str(target.resolve())!r}, 'w')\n"
        manifest = self.manifest(filesystem_allowlist=(str(data.resolve()),))
        with pytest.raises(ContractError, match="containment"):
            run_sandboxed(manifest, source, "go")

    def test_host_callback_filesystem_emulation_is_rejected(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        manifest = self.manifest(filesystem_allowlist=(str(data.resolve()),))
        with pytest.raises(ContractError, match="host callback"):
            run_sandboxed(
                manifest, "def go():\n    return 1\n", "go",
                read_file_bytes=lambda _: b"not-used",
            )

    def test_benign_module_runs(self):
        source = "def add(a, b):\n    return a + b\n"
        assert run_sandboxed(self.manifest(), source, "add", 2, 3) == 5

    def test_spawned_process_cannot_write_host_filesystem(self, tmp_path):
        marker = tmp_path / "host-escape-marker"
        parent = marker.parent
        source = (
            "def go():\n"
            "    import os\n"
            f"    return os.system('mkdir -p {parent} && touch {marker}')\n"
        )
        # Process execution inside the jail is allowed; the proof is that the
        # child sees an isolated /tmp and cannot mutate the host path.
        assert run_sandboxed(self.manifest(), source, "go") == 0
        assert not marker.exists()


# ---------------------------------------------------------------- ENT5-R8


class TestReproducible:
    def manifest(self):
        return BuildManifest(
            version="1.0.0",
            inputs={"src/main.py": sha(b"src")},
            outputs={"dist/a.whl": sha(b"A"), "dist/b.whl": sha(b"B")},
            environment={"python": "3.12", "os": "linux"},
        )

    def test_bit_identical_rebuild_verified(self):
        manifest = self.manifest()
        report = verify_reproducible(manifest, rebuild=lambda m: dict(m.outputs))
        assert report.reproducible
        assert report.verified_outputs == ("dist/a.whl", "dist/b.whl")
        assert report.manifest_sha256 == manifest.sha256

    def test_mismatch_detected(self):
        manifest = self.manifest()

        def bad_rebuild(m):
            out = dict(m.outputs)
            out["dist/b.whl"] = sha(b"tampered")
            return out

        report = verify_reproducible(manifest, rebuild=bad_rebuild)
        assert not report.reproducible
        assert report.mismatched_outputs == ("dist/b.whl",)

    def test_missing_output_detected(self):
        manifest = self.manifest()
        report = verify_reproducible(manifest, rebuild=lambda m: {"dist/a.whl": sha(b"A")})
        assert not report.reproducible
        assert report.mismatched_outputs == ("dist/b.whl",)

    def test_environment_mismatch_rejected(self):
        manifest = self.manifest()
        with pytest.raises(ContractError, match="environment"):
            verify_reproducible(
                manifest, rebuild=lambda m: dict(m.outputs), environment={"python": "3.11"}
            )

    def test_environment_match_accepted(self):
        manifest = self.manifest()
        report = verify_reproducible(
            manifest, rebuild=lambda m: dict(m.outputs), environment=dict(manifest.environment)
        )
        assert report.reproducible


# ------------------------------------------------------- docstring coverage


class TestDocstringRequirementIds:
    def test_public_api_docstrings_mention_requirements(self):
        import inspect

        import residual.supplychain as sc

        required = {
            "signing": ("ENT5-R1",),
            "sbom": ("ENT5-R2", "ENT5-R3"),
            "audit": ("ENT5-R4",),
            "disclosure": ("ENT5-R5",),
            "pinning": ("ENT5-R6",),
            "sandbox": ("ENT5-R7",),
            "reproducible": ("ENT5-R8",),
        }
        for mod_name, req_ids in required.items():
            module = __import__(f"residual.supplychain.{mod_name}", fromlist=["*"])
            assert module.__doc__, f"{mod_name} missing module docstring"
            for req in req_ids:
                assert req in module.__doc__, f"{mod_name} docstring missing {req}"
            for _, obj in inspect.getmembers(module):
                if inspect.isclass(obj) or inspect.isfunction(obj):
                    if obj.__module__ != module.__name__ or obj.__name__.startswith("_"):
                        continue
                    doc = inspect.getdoc(obj) or ""
                    assert any(
                        req in doc for req in req_ids
                    ), f"{mod_name}.{obj.__name__} docstring missing requirement ID"
