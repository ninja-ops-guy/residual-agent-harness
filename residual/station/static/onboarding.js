"use strict";

(() => {
  const dialog = document.querySelector("#first-run");
  if (!dialog || typeof dialog.showModal !== "function") return;

  const DISMISSED = "residual-onboarding-v1-dismissed";
  const PROJECT = "residual-project";

  function shouldOpen() {
    return !localStorage.getItem(PROJECT) && localStorage.getItem(DISMISSED) !== "1";
  }

  function stationReady() {
    return Boolean(document.querySelector("#main .page-heading"));
  }

  function openFirstRun() {
    if (shouldOpen() && !dialog.open) dialog.showModal();
  }

  function openWhenReady(attempt = 0) {
    if (stationReady()) {
      openFirstRun();
      return;
    }
    if (attempt < 80) window.setTimeout(() => openWhenReady(attempt + 1), 100);
  }

  function dismiss() {
    localStorage.setItem(DISMISSED, "1");
    if (dialog.open) dialog.close();
  }

  // Wait for app.js to finish the authenticated station bootstrap and render a real view.
  window.addEventListener("load", () => openWhenReady(), {once: true});

  dialog.addEventListener("cancel", event => {
    event.preventDefault();
    dismiss();
  });

  dialog.addEventListener("click", event => {
    if (event.target.closest("[data-onboarding-dismiss]")) {
      dismiss();
      return;
    }

    // The existing app.js `demo` action owns mission creation + queueing.
    // We only close the onboarding shell; successful creation writes PROJECT.
    if (event.target.closest("[data-onboarding-run]")) {
      dialog.close();
    }
  });

  document.addEventListener("change", event => {
    if (event.target.id === "project-select" && event.target.value && dialog.open) {
      dialog.close();
    }
  });
})();
