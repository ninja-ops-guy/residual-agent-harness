# AX-21 / R4 Observation — Promotion Can Reinterpret Previously Validated Authority

**Observation ID:** AX21-OBS-R4-PROMOTION-20260925-005  
**Date:** 2026-09-25  
**Status:** OBSERVED / CORPUS EVIDENCE  
**Campaign:** SNYK-R4-02 independent adversarial review  
**Reviewed HEAD:** 2b75b42cd8cf1a7f13eac64a77d86ddfb619d169  
**Reviewed tree:** 82ffc85b5d7611b08c9cc9c16ba2bebfc5604f14

## Observation

A symlink target can satisfy confinement while interpreted relative to a private staging directory and become outside-authoritative after the staged tree is renamed into its final runtime location.

The reproduced construction used a target shaped like:

```
../../.runtime-install-<known-name>/runtime/victim
```

Before promotion, the target resolves inside the staging authority. After the staged runtime directory is renamed to the authoritative runtime path, the same symlink text is interpreted from a different location and can resolve outside the promoted runtime.

The independent adversarial probe reproduced this for TAR and TAR.ZST and performed a bounded follow-up write through the promoted link. ZIP rejected equivalent symlink metadata.

## Important condition

The demonstrated construction requires the archive to know or correctly guess the staging basename. The reproduction controlled temporary-name generation to make that condition deterministic. An incorrect-name control was rejected.

No staging-name discovery channel or practical remote exploitation was established by this observation. The result nevertheless disproves the stronger invariant that staging-relative validation alone guarantees confinement after relocation.

## Candidate invariant

**AX21-AUTH-RELOC-01 — Authority Must Be Stable Across State Transitions**

> If an object is validated under one namespace, root, mount, path, identity, or authority context and is later promoted into another, the verifier must prove that the object's effective authority remains valid under the post-transition interpretation. Pre-transition validity is insufficient when the transition can change meaning.

## Security consequence

The previous R4-02 contract successfully addressed:
- pre-extraction member validation;
- explicit link validation;
- disposable staging;
- post-extraction validation;
- failed-extraction rollback;
- runtime security floors.

But the verifier evaluated link authority in the staging namespace, while the final rename changed the namespace in which relative link targets were interpreted.

Thus:

```
valid_in_staging != necessarily_valid_after_promotion
```

This is a state-transition validation gap rather than a failure of the original GNU-tar finding, runtime floor, CI evidence, or receipt integrity.

## Research implications

1. **Validation context is part of the evidence.** A value cannot be called safe without specifying the namespace/context under which it was interpreted.
2. **Promotion is a semantic transformation.** Rename/move/publish operations can change effective authority even when bytes are unchanged.
3. **Post-validation must target authoritative state.** A staging tree may need validation against its eventual destination semantics before promotion, or links may need a representation whose authority is invariant under relocation.
4. **Green qualification can coexist with an untested invariant.** The exact-head CI evidence remained sound for the tests it ran; 83 archive tests did not cover this relocation condition.
5. **Negative controls should include state-transition mutations.** Testing extraction alone is insufficient when promotion changes interpretation.

## Candidate regression experiment

Construct a staged tree containing:
- a benign confined relative link;
- a relocation-sensitive relative link whose staging interpretation is confined but promoted interpretation escapes;
- an incorrect-name control.

Verify:
1. benign confined links retain intended authority after promotion;
2. relocation-sensitive links are rejected before authoritative publication;
3. incorrect-name controls remain rejected;
4. TAR and TAR.ZST enforce equivalent semantics;
5. ZIP remains explicit about unsupported link metadata.

Mutation control: remove destination-context validation and prove the relocation-sensitive case becomes publishable.

## Broader AX-21 application

The same pattern should be tested in:
- worktree/staging-to-main promotion;
- worker lease ownership transitions;
- provider endpoint redirects;
- temporary-to-authoritative evidence receipts;
- sandbox-to-host artifact publication;
- extension/plugin installation roots;
- identity/generation changes during reassignment.

The general question is:

> Does the meaning of previously validated authority change when the object crosses the next state boundary?

## Limitations

This is a deterministic bounded reproduction, not a demonstrated remote exploit. It assumes knowledge or correct guessing of the temporary staging basename. Resource exhaustion, hostile local mutation, and native-platform archive behavior remain outside this observation.
