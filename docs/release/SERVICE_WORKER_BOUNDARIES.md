# Service Worker Boundary Map

## Root Pages COI worker

The root `site/coi-serviceworker.js` may control same-origin Pages paths. Its response rewriting is required for the WebVM surface but MUST be path-aware.

- `/demo/**`: COOP/COEP/CORP behavior required by WebVM. Must remain cross-origin isolated.
- `/provider/**`: explicit same-origin bypass. Fetch the original response without injecting WebVM COOP/COEP headers. Must remain non-isolated so external provider SDK resources can initialize.
- other paths: follow the root site's intended COI behavior; any expansion of exemptions requires explicit review.

## WebVM worker

`/demo/serviceWorker.js` belongs to the generated WebVM runtime and is independently identity-bound in `build-info.json`. Do not conflate it with the root Pages COI worker.

## Change rule

Any modification to worker registration, scope, response headers, navigation, path layout, or provider location requires testing both `/demo/` and `/provider/` on the published origin. A local static server cannot reproduce all root service-worker policy interactions and therefore is not sufficient production evidence.
