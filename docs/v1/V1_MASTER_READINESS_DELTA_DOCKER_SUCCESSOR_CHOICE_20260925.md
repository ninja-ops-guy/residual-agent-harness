# V1 master delta — competing Docker successor identity

Status: append-only coordination note. No implementation branch is edited and no physical or release authority is granted.

## Exact observation

Two open AUD-1/container successors currently diverge from the same frozen #448 base `943c77a28ada1bc3931408c5f9b40d40c25eb2dc`:

- #462 `be0fe1087b51bb7c032cb6175d778735e69be4a7` — loopback-bound Station plus container-facing forwarding.
- #469 `935498ecd42982bc682d7ed69b562c642b74a8fe` — explicit container-local-only exposure contract while retaining the image's container-interface bind.

Git comparison reports the two heads as **diverged**, with their merge base exactly #448. Neither head is a descendant of the other. Both are draft and had zero submitted human reviews at this observation.

#469 exact-head Command Station evidence includes a successful real default `docker compose up --build -d` exercise, bootstrap probe, and spoofed non-loopback Host rejection. Qualification-v1 and surrounding technical workflows also PASS. This is technical candidate evidence, not selection.

## Gate consequence

Stable ID: `AUD1-CONTAINER-CHOICE-01`

Acceptance criterion: one exact Docker/container successor must be explicitly selected or rejected by the AUD-1 owner before helper rebinding and physical F6. Competing divergent implementations must not both be treated as the selected candidate.

Classification: scope/implementation decision.

Status: **BLOCKED** on AUD-1 owner disposition.

Required human action: review #462 versus #469 against the recorded D1 container-support requirement and select one exact head (or request a new reconciled successor). After selection, rebind/requalify the F6 helper to that exact candidate before any separately authorized physical F6.

The existing #448/#455 approval evidence remains valid historical evidence for those exact bytes only; it does not transfer automatically to either Docker successor.
