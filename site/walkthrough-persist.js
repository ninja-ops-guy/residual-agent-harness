(() => {
  const KEY = 'residual.walkthrough.v1';
  const defaults = { tab: 'walk', steps: 0, ran: false };
  let restoring = true;

  function read() {
    try {
      return { ...defaults, ...JSON.parse(localStorage.getItem(KEY) || '{}') };
    } catch (_) {
      return { ...defaults };
    }
  }

  function write(next) {
    try { localStorage.setItem(KEY, JSON.stringify(next)); } catch (_) {}
  }

  function clear() {
    try { localStorage.removeItem(KEY); } catch (_) {}
  }

  function install() {
    const stepBtn = document.getElementById('step');
    const runBtn = document.getElementById('run');
    const resetBtn = document.getElementById('reset');
    const tabs = [...document.querySelectorAll('[data-tab]')];
    if (!stepBtn || !runBtn || !resetBtn || !tabs.length) return;

    let state = read();

    tabs.forEach(btn => btn.addEventListener('click', () => {
      if (restoring) return;
      state.tab = btn.dataset.tab || 'walk';
      write(state);
    }));

    stepBtn.addEventListener('click', () => {
      if (restoring) return;
      state.steps = Math.min(12, (state.steps || 0) + 1);
      state.ran = false;
      write(state);
    });

    runBtn.addEventListener('click', () => {
      if (restoring) return;
      state.ran = true;
      state.steps = 12;
      write(state);
    });

    resetBtn.addEventListener('click', () => {
      if (restoring) return;
      state = { ...defaults };
      clear();
    });

    // Restore the view first, then replay the deterministic walkthrough state.
    const tab = tabs.find(btn => btn.dataset.tab === state.tab);
    if (tab) tab.click();

    if (state.ran) {
      // Re-run the deterministic presentation so timers/evidence stream are rebuilt.
      setTimeout(() => runBtn.click(), 80);
    } else if (state.steps > 0) {
      const count = Math.min(12, Number(state.steps) || 0);
      for (let i = 0; i < count; i++) stepBtn.click();
    }

    restoring = false;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, { once: true });
  } else {
    install();
  }
})();
