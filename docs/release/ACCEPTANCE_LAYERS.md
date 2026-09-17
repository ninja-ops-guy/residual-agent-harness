# Browser Demo Acceptance Layers

Report these independently. Never infer one from another.

| Layer | Required evidence | Does not prove |
|---|---|---|
| Artifact identity | published build-info SHA + hashes | browser/runtime health |
| Generated WebVM | generated artifact desktop/narrow real guest proof | published-origin behavior |
| Published WebVM | first production deployment real guest proof | external provider SDK |
| Provider fixture | deterministic SDK double, protocol/auth/error behavior | external SDK network/policy |
| Provider SDK load | published `/provider/` loads real `js.puter.com/v2/` | sign-in or inference |
| Provider auth | real user completes sign-in | model protocol correctness |
| Provider inference | retained real model call reaches RESIDUAL candidate path | physical-device runtime |
| Physical device | actual target browser/device execution | other device engines |

Use PASS, FAIL, NOT_RUN, UNKNOWN, or BLOCKED per layer. A release summary must not replace NOT_RUN/UNKNOWN with PASS because another layer is green.
