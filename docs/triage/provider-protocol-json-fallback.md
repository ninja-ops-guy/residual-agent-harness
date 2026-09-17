# Live provider protocol compatibility fallback

Status: implementation candidate for review. This document records the narrow production-demo defect and the intended trust boundary; it is not execution evidence.

## Retained live symptom

On accepted production `main@2b7cb626a9a327cf56ede847fa4e6ae6cdf9243f`, a real-account iPhone/WebKit build mission reached the remote provider twice and both counted calls ended with the safe code `provider_protocol_invalid`. The mission remained blocked, accepted zero obligations, generated no files, and retained semantic verification as UNKNOWN. The raw provider response was not retained and must not be inferred from the safe code.

## Compatibility boundary

The browser bridge already accepts only the exact RESIDUAL `updates` / `requests` worker envelope and fails closed on malformed tool arguments, prose, wrong keys, or otherwise invalid structure. That validator remains authoritative and unchanged.

Puter's public browser chat surface forwards the `tools` option, but its current client-side option forwarding does not expose `tool_choice` to callers. Therefore a browser caller cannot rely on forcing the model to invoke `residual_submit` even when the tool is supplied.

## Bounded repair

The first provider request keeps the existing tool transport. If that counted request returns `provider_protocol_invalid`, the provider grant records a local compatibility state of `json`. Nothing is retried inside that request.

If and only if RESIDUAL later dispatches another request under the same already-bounded mission grant, that separately counted call omits tools and instructs the model to return the exact raw JSON worker envelope as its entire response. The same parser validates the response afterward. A second invalid response remains a failure.

This preserves:

- the core provider-call budget and cost accounting;
- one `sdk.ai.chat()` call per RESIDUAL inference request;
- the existing exact worker-envelope validator;
- provider/model selection authority;
- M4 and protected qualification boundaries;
- BLOCKED/UNKNOWN semantics when no candidate is accepted.

## Non-claims

This candidate does not establish live Puter success, provider quality, production readiness, blank-machine qualification, host-loss recovery, elapsed soak, or research evidence. Browser/test-double qualification is not a substitute for a fresh real-account iPhone/WebKit run after an accepted revision is deployed.
