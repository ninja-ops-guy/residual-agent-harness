(() => {
  const KEY = 'residual.walkthrough.v1';
  const CONSENT = 'residual.walkthrough.consent.v1';
  const LIFETIME = 180 * 24 * 60 * 60 * 1000;
  const defaults = {tab: 'walk', steps: 0, ran: false};
  let restoring = true;
  function install() {
    const stepBtn = document.getElementById('step');
    const runBtn = document.getElementById('run');
    const resetBtn = document.getElementById('reset');
    const tabs = [...document.querySelectorAll('[data-tab]')];
    if (!stepBtn || !runBtn || !resetBtn || !tabs.length) return;
    const controls = document.createElement('div');
    controls.className = 'residual-privacy-control';
    controls.innerHTML = '<label><input type="checkbox" id="remember-walkthrough"> Remember walkthrough progress for up to 180 days on this browser</label><a href="../legal/cookies.html">Storage and privacy choices</a><span id="remember-status" role="status" aria-live="polite"></span>';
    const host = resetBtn.closest('main') || document.querySelector('main') || document.body;
    host.prepend(controls);
    const choice = controls.querySelector('#remember-walkthrough');
    const status = controls.querySelector('#remember-status');
    let state = {...defaults}, expires = 0;
    const clear = () => {
      localStorage.removeItem(CONSENT);
      localStorage.removeItem(KEY);
    };
    function failure() {
      expires = 0; choice.checked = false;
      try { clear(); } catch (_) {}
      status.textContent = ' Storage unavailable. The walkthrough still works without saving; use browser settings to remove any older saved data.';
    }
    function currentConsent() {
      const saved = JSON.parse(localStorage.getItem(CONSENT) || 'null');
      return saved?.version === 1 && Number.isFinite(saved.expires) && saved.expires > Date.now() && saved.expires <= Date.now() + LIFETIME ? saved.expires : 0;
    }
    function write() {
      // Recheck the stored choice at every write: another tab may have withdrawn it.
      try {
        if (!choice.checked || !expires) return;
        const allowed = currentConsent();
        if (!allowed || allowed !== expires) { expires = 0; choice.checked = false; clear(); return; }
        localStorage.setItem(KEY, JSON.stringify(state));
      } catch (_) { failure(); }
    }
    try {
      expires = currentConsent();
      choice.checked = !!expires;
      if (expires) {
        const saved = JSON.parse(localStorage.getItem(KEY) || 'null');
        if (saved && tabs.some(tab => tab.dataset.tab === saved.tab) && Number.isInteger(saved.steps) && saved.steps >= 0 && saved.steps <= 12 && typeof saved.ran === 'boolean') state = {tab: saved.tab, steps: saved.steps, ran: saved.ran};
      } else clear(); // Do not restore legacy progress without an explicit choice.
    } catch (_) { try { clear(); } catch (_) {} failure(); }
    choice.addEventListener('change', () => {
      try {
        if (choice.checked) {
          expires = Date.now() + LIFETIME;
          localStorage.setItem(CONSENT, JSON.stringify({version: 1, expires}));
          write();
          if (choice.checked) status.textContent = ' Progress will be remembered. Uncheck to remove it.';
        } else {
          expires = 0; clear();
          status.textContent = ' Saved progress removed. This page continues without saving.';
        }
      } catch (_) { try { clear(); } catch (_) {} failure(); }
    });
    window.addEventListener('storage', event => {
      if (event.key !== CONSENT && event.key !== null) return;
      try {
        if (!currentConsent()) {
          choice.checked = false; expires = 0;
          // Withdrawal elsewhere must not silently re-enable saving here.
          localStorage.removeItem(KEY);
          status.textContent = ' Remembering was turned off in another tab.';
        }
      } catch (_) { failure(); }
    });
    tabs.forEach(btn => btn.addEventListener('click', () => {
      if (restoring) return;
      state.tab = btn.dataset.tab || 'walk'; write();
    }));
    stepBtn.addEventListener('click', () => {
      if (restoring) return;
      state.steps = Math.min(12, state.steps + 1); state.ran = false; write();
    });
    runBtn.addEventListener('click', () => {
      if (restoring) return;
      state.ran = true; state.steps = 12; write();
    });
    resetBtn.addEventListener('click', () => {
      if (restoring) return;
      state = {...defaults};
      try { localStorage.removeItem(KEY); } catch (_) { failure(); }
    });
    tabs.find(btn => btn.dataset.tab === state.tab)?.click();
    if (state.ran) {
      setTimeout(() => { runBtn.click(); restoring = false; }, 80);
    } else {
      for (let i = 0; i < state.steps; i++) stepBtn.click();
      restoring = false;
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once: true});
  else install();
})();
