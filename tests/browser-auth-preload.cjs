/* Test-only adapter for the Station's one-time authenticated launch URL.
 *
 * Production no longer returns operator authority from /api/bootstrap. The server
 * prints a one-time /auth/<capability> URL. Existing browser journeys intentionally
 * exercise the real UI, so this preload captures that URL from the child Station
 * process and substitutes it for the first same-origin page.goto().
 */
const childProcess = require('node:child_process');
const originalSpawn = childProcess.spawn;
childProcess.spawn = function (...args) {
  const child = originalSpawn.apply(this, args);
  const argv = Array.isArray(args[1]) ? args[1] : [];
  if (argv.includes('residual.station.server') && child.stdout) {
    child.stdout.on('data', chunk => {
      const match = String(chunk).match(/Open (https?:\/\/\S+\/auth\/\S+)/);
      if (match) global.__RESIDUAL_STATION_AUTH_URL = match[1];
    });
  }
  return child;
};

const playwright = require('playwright');
for (const name of ['chromium', 'firefox', 'webkit']) {
  const type = playwright[name];
  if (!type || type.__residualAuthWrapped) continue;
  type.__residualAuthWrapped = true;
  const originalLaunch = type.launch.bind(type);
  type.launch = async options => {
    const browser = await originalLaunch(options);
    const originalNewContext = browser.newContext.bind(browser);
    browser.newContext = async contextOptions => {
      const context = await originalNewContext(contextOptions);
      const originalNewPage = context.newPage.bind(context);
      context.newPage = async () => {
        const page = await originalNewPage();
        const originalGoto = page.goto.bind(page);
        let authenticated = false;
        page.goto = async (target, gotoOptions) => {
          const launch = global.__RESIDUAL_STATION_AUTH_URL;
          if (!authenticated && launch) {
            const wanted = new URL(String(target));
            const auth = new URL(launch);
            if (wanted.origin === auth.origin) {
              authenticated = true;
              return originalGoto(launch, gotoOptions);
            }
          }
          return originalGoto(target, gotoOptions);
        };
        return page;
      };
      return context;
    };
    return browser;
  };
}
