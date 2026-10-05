/* Required import in generated provider.js: missing module fails closed. */
export function installProviderPrivacy({onWithdraw, reload = () => location.reload()} = {}) {
  const load = document.getElementById('load');
  const withdraw = document.getElementById('provider-privacy-withdraw');
  if (!load || !withdraw || typeof onWithdraw !== 'function') throw new Error('provider_privacy_controls_missing');
  let started = false, ticket = false;
  // Feature-led choice: the disclosed Load button, not a saved login or page visit.
  load.addEventListener('click', event => {
    if (!event.isTrusted) return;
    ticket = true;
    setTimeout(() => { ticket = false; }, 0);
  }, true);
  const reset = () => {
    ticket = false;
    onWithdraw();
    if (started) reload();
  };
  withdraw.addEventListener('click', reset);
  window.addEventListener('pageshow', event => { if (event.persisted) reset(); });
  return Object.freeze({
    allowLoad() {
      if (!ticket) {
        const status = document.getElementById('status');
        if (status) status.textContent = 'Optional provider software is off. Use the Load Puter button to enable it after reading the privacy notice.';
        return false;
      }
      ticket = false;
      started = true;
      return true;
    }
  });
}
