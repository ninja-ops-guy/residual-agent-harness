"use strict";

(() => {
  const dialog = document.querySelector("#first-run");
  if (!dialog || typeof dialog.showModal !== "function") return;

  const DISMISSED = "residual-onboarding-v1-dismissed";
  const PROJECT = "residual-project";

  function shouldOpen() {
    return !localStorage.getItem(PROJECT) && localStorage.getItem(DISMISSED) !== "1";
  }

  function openFirstRun() {
    if (shouldOpen() && !dialog.open) dialog.showModal();
  }

  function dismiss() {
    localStorage.setItem(DISMISSED, "1");
    if (dialog.open) dialog.close();
  }

  // Defer until Command Station has had a chance to render its bootstrap state.
  window.addEventListener("load", () => requestAnimationFrame(openFirstRun), {once: true});

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
