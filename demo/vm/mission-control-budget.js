import {mountMissionControl as mountWorld} from './mission-control-world.js';

const BUILD_OUTPUT_TOKENS = 8192;
const LIVE_OUTPUT_TOKENS = 1536;

export function mountMissionControl(host) {
  const control = mountWorld(host);
  const root = document.querySelector('#mission-control');
  const mode = root?.querySelector('#mc-mode');
  const tokens = root?.querySelector('#mc-tokens');

  function syncBudget() {
    if (!mode || !tokens) return;
    const value = Number(tokens.value);
    if (mode.value === 'build') {
      tokens.max = String(BUILD_OUTPUT_TOKENS);
      if (!Number.isFinite(value) || value < 256 || value <= LIVE_OUTPUT_TOKENS) {
        tokens.value = String(BUILD_OUTPUT_TOKENS);
      }
      return;
    }
    tokens.max = String(LIVE_OUTPUT_TOKENS);
    if (!Number.isFinite(value) || value < 256 || value > LIVE_OUTPUT_TOKENS) {
      tokens.value = String(LIVE_OUTPUT_TOKENS);
    }
  }

  mode?.addEventListener('change', syncBudget);
  syncBudget();

  return {
    ...control,
    destroy() {
      mode?.removeEventListener('change', syncBudget);
      control.destroy();
    }
  };
}
