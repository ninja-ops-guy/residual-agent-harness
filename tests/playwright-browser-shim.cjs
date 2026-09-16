/* Adapter for tests/browser.cjs so the same user journey can qualify Chromium,
 * Firefox, and WebKit without changing the production UI harness. */
const playwright = require('playwright');
const name = process.env.PLAYWRIGHT_BROWSER || 'chromium';
if (!['chromium', 'firefox', 'webkit'].includes(name)) {
  throw new Error(`Unsupported PLAYWRIGHT_BROWSER=${name}`);
}
const selected = playwright[name];
module.exports = {
  chromium: {
    async launch(options = {}) {
      if (name === 'chromium') return selected.launch(options);
      const { executablePath, args, ...portable } = options;
      return selected.launch(portable);
    },
  },
};
