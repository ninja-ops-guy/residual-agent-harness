# EXECUTION-SUBSTRATE-SPI-R0 — Governed Runtime Substrates

**Status:** post-v1 architecture candidate  
**Date:** 2026-09-30  
**Depends on:** SPEC-ADAPTER-OPENSHELL-R0, execution-engine protocol, Factory/Station authority contracts  
**Release effect:** none on v1 unless new evidence shows violation of an existing v1 invariant

## Purpose

Separate two questions that RESIDUAL previously risked combining:

1. **Execution engine:** which model/agent/framework performs work?
2. **Execution substrate:** which independently enforced runtime boundary is allowed to execute that work?

RESIDUAL remains the authority/control plane. A substrate never becomes an
acceptance authority merely because it successfully executed a process.

## Architecture

    Goal / Mission / Worker Contract
                  |
                  v
          RESIDUAL Authority
                  |
                  v
           Engine Selection
      Hermes / OpenClaw / CrewAI / ...
                  |
                  v
      QualifiedSubstrateRouter
                  |
          exact qualification tuple
                  |
           +------+-------------------+------------------+
           |                          |                  |
           v                          v                  v
       OpenShell                FactoryRuntime       future
     Docker/VM/K8s/...          local bounded        TEE / cloud
           |                          |                  |
           +--------------------------+------------------+
                                      |
                                      v
                           observable evidence only
                                      |
                                      v
                    verifier -> byte admission -> integrator
                                      |
                                      v
                             Station / human authority

## Why this is stronger than an OpenShell-only integration

OpenShell becomes the first high-value substrate implementation rather than a
hard dependency in the RESIDUAL trust model.

That gives RESIDUAL:

- vendor-independent orchestration;
- deterministic routing between execution boundaries;
- independent qualification of each driver/platform/agent combination;
- a path to enterprise-native sandboxes without redesigning Station;
- a path to confidential-compute/TEE substrates later;
- fallback between qualified substrates without weakening verification;
- a durable answer to "who controls the shell?" that does not make the shell
  provider authoritative over accepted state.

## Exact qualification tuple

A substrate qualification is bound to:

    substrate name
    substrate version
    substrate source identity
    compute driver
    platform class
    environment digest
    agent profile
    agent identity
    image digest
    requested policy digest
    provider profile/config set digest
    inference route digest

Changing any member creates a different tuple and therefore requires an
independently admissible qualification record.

The environment digest is intended to cover host/runtime facts that materially
affect enforcement, such as OS/kernel, architecture, compute-runtime version,
Landlock/security primitive state, and driver-relevant configuration.

## Qualification is derived, not asserted

A SubstrateQualificationRecord contains gate attempts and evidence digests.

Overall status is mechanically derived:

- any required FAIL -> FAIL
- otherwise any required BLOCKED -> BLOCKED
- otherwise any required UNKNOWN -> UNKNOWN
- all required PASS -> PASS

Capabilities are published only from a PASS record.

There is deliberately no free-form secure=true flag.

## Persistent qualification ledger

SubstrateQualificationLedger serializes records canonically and content-addresses
the ledger.

The ledger is evidence distribution, not authority. Station still decides whether
a record is admissible for a mission.

The same ledger can be:

- stored with release evidence;
- transported over Shared Comms;
- displayed in Station;
- replicated to fleet seats;
- compared between releases;
- used by the routing layer;
- fed into an enterprise qualification control plane.

## Qualified routing

QualifiedSubstrateRouter requires a pinned PASS record.

Routing checks:

1. runtime identity matches the exact tuple;
2. substrate health is healthy;
3. required capabilities exist in the pinned PASS;
4. requested driver/platform/profile constraints match;
5. deterministic tie breaking is used.

Locality may be used as a deterministic preference only after all security and
capability gates pass.

## OpenShell mapping

OpenShell is especially suitable because its current architecture exposes a
gateway control plane and per-sandbox supervisor boundary, while compute,
credential, control-plane identity and sandbox identity are explicit integration
boundaries.

| RESIDUAL concept | OpenShell source |
|---|---|
| substrate | OpenShell sandbox |
| substrate control endpoint | Gateway / Python SDK |
| enforcement boundary | sandbox Supervisor + kernel/runtime controls |
| requested policy | RESIDUAL-compiled policy IR translated to OpenShell policy |
| base policy evidence | OpenShell base policy |
| effective policy evidence | base + applicable provider layers |
| credentials | attached provider profiles / placeholder resolution |
| security observations | OCSF events |
| lifecycle evidence | sandbox state + canonical process/exec results |
| compute driver | Docker, Podman, Kubernetes, MicroVM/VM-class driver |
| machine API | OpenShell Python SDK or structured CLI output |

At the time of this R0, NVIDIA documents OpenShell 0.1.x and a Python SDK
(openshell package, Python 3.11+) with SandboxClient. A live RESIDUAL client
should prefer the SDK over parsing human CLI text. The SDK and gateway should be
kept on the same OpenShell release where possible.

## Provider identity is part of qualification

Provider names are insufficient for exact qualification.

Current OpenShell provider profiles can define credentials, allowed endpoints,
allowed binaries, provider-owned network policy, and refresh behavior.

Therefore RESIDUAL exact qualification binds a digest of provider profile/config
identity. An execution request using the same provider name but a different
profile/config does not inherit the previous PASS.

## Base versus effective policy

OpenShell currently distinguishes base policy from effective policy. Attached
providers may contribute policy layers.

RESIDUAL therefore records three separate facts:

    requested_policy_digest
    base_policy_digest
    effective_policy_digest

They are not required to be byte-identical. Qualification proves the
translation/composition relationship and runs negative probes against the
effective enforcement.

## OCSF evidence

OpenShell can emit OCSF security events and full OCSF JSONL.

RESIDUAL should ingest them with vendor provenance. They remain vendor
observations until a RESIDUAL verifier independently derives a claim from them.

A future Security Evidence Fabric adapter can correlate those events against
host, network, IAM, source-control, Station and other evidence.

## Bounded self-build mode

SelfBuildContract makes "RESIDUAL builds RESIDUAL" a governed mode.

R0 deliberately forbids the worker from holding:

- repository write authority;
- accepted-state write authority;
- merge authority.

The first credible chain is:

    frozen self-build mission
     -> qualified substrate
     -> sandboxed agent authors bounded change
     -> expected artifacts only
     -> byte-exact verification
     -> independent verifier
     -> deterministic integration into disposable candidate
     -> completion receipt
     -> STOP before merge

A later authority tier may introduce repository-write capability, but it must be
qualified separately and must not silently replace the R0 boundary.

## Capability taxonomy

Suggested substrate capabilities:

    sandboxed_execution
    filesystem_policy
    network_policy
    process_identity
    resource_limits
    credential_broker
    provider_endpoint_binding
    artifact_manifest
    artifact_byte_identity
    security_observability
    ocsf_export
    managed_inference
    gpu_execution
    driver_docker
    driver_podman
    driver_kubernetes
    driver_microvm
    agent_hermes
    agent_openclaw
    agent_codex

Capabilities describe proven properties, not marketing categories.

## OpenShell qualification milestones

### OS-A — contract/core

- immutable execution request;
- policy IR;
- evidence schema;
- exact qualification tuple;
- qualification ledger;
- qualified router;
- bounded self-build contract.

### OS-B — direct Docker qualification

- exact OpenShell release and binary identity;
- exact image digest;
- base/effective policy evidence;
- Landlock/filesystem negative tests;
- network negative tests;
- process identity;
- provider placeholder and endpoint-binding tests;
- lifecycle/timeout/orphan tests;
- OCSF evidence capture;
- artifact manifest and one-byte mutation test.

### OS-C — Hermes

Repeat OS-B with exact Hermes/NemoClaw profile and model/provider identity.

### OS-D — OpenClaw

Independent qualification; Hermes evidence cannot substitute.

### OS-E — bounded self-build

Reach SELF_BUILD_BOUNDED_PASS against a disposable candidate.

### OS-F — fleet

Distribute qualification ledger over Shared Comms and allow Station to select
qualified seats/substrates.

### OS-G — enterprise

- Kubernetes driver qualification;
- workload identity / enterprise provider profiles;
- OIDC/service auth for remote gateways;
- SIEM export;
- centralized policy administration;
- independent operator reproduction.

### OS-H — confidential/high-assurance

Add qualified VM/microVM/TEE substrates where they provide materially stronger
isolation; preserve the same RESIDUAL authority and evidence contracts.

## Production invariants

1. A substrate PASS never equals candidate acceptance.
2. An engine cannot self-assert a substrate capability.
3. Routing cannot select an unqualified tuple.
4. Qualification cannot move across drivers/platforms/images/policies/providers.
5. Unknown enforcement state is UNKNOWN, not PASS.
6. Hidden retries do not erase first failure.
7. Agent success claims have no authority.
8. Artifact success does not replace byte-exact admission.
9. Provider credentials never need to become RESIDUAL task/context plaintext.
10. Self-build remains bounded by independent authority.

## Current upstream anchors used for this design

Revalidate at qualification time:

- https://docs.nvidia.com/openshell/about/how-it-works
- https://docs.nvidia.com/openshell/dev/sdk/python
- https://docs.nvidia.com/openshell/latest/how-it-works/policies/overview
- https://docs.nvidia.com/openshell/sandboxes/providers-v2
- https://docs.nvidia.com/openshell/observability/ocsf-json-export
- https://docs.nvidia.com/openshell/dev/how-it-works/sandboxes/overview
- https://github.com/NVIDIA/OpenShell/releases

No upstream statement is treated as proof of a RESIDUAL qualification gate.
