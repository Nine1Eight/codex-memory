const countNode = document.getElementById("count");
const thresholdNode = document.getElementById("threshold");
const lockStateNode = document.getElementById("lock-state");
const apiLabelNode = document.getElementById("api-label");
const statePillNode = document.getElementById("state-pill");
const lookiOutputNode = document.getElementById("looki-output");
const loadLookiButton = document.getElementById("load-looki");
const loadMomentsButton = document.getElementById("load-moments");
const apiBase = window.AGENTVIEW_API_BASE_URL || window.location.origin;
const defaultBootstrap = { count: 0, threshold: "?", locked: true };

thresholdNode.textContent = defaultBootstrap.threshold;
countNode.textContent = "0";
lockStateNode.textContent = "Locked until qualified multimodal views reach the threshold.";
apiLabelNode.textContent = apiBase === window.location.origin ? "auto" : apiBase;

fetch(`${apiBase}/setup/status`)
  .then((response) => response.json())
  .then((status) => {
    const bootstrap = status.bootstrap || defaultBootstrap;
    countNode.textContent = String(bootstrap.count);
    thresholdNode.textContent = String(bootstrap.threshold);
    const locked = Boolean(bootstrap.locked);
    lockStateNode.textContent = locked
      ? "Locked until qualified multimodal views reach the threshold."
      : "Unlocked for recommendations and production rankings.";
    statePillNode.textContent = locked ? "locked" : "unlocked";
  })
  .catch(() => {
    lockStateNode.textContent = "Offline preview. Connect the API to show live bootstrap status.";
    statePillNode.textContent = "offline";
  });

function showLooki(value) {
  lookiOutputNode.textContent = JSON.stringify(value, null, 2);
}

loadLookiButton?.addEventListener("click", () => {
  fetch(`${apiBase}/looki/me`)
    .then((response) => response.json())
    .then(showLooki)
    .catch(() => showLooki({ error: "unable to load Looki /me" }));
});

loadMomentsButton?.addEventListener("click", () => {
  const today = new Date().toISOString().slice(0, 10);
  fetch(`${apiBase}/looki/moments?on_date=${today}`)
    .then((response) => response.json())
    .then(showLooki)
    .catch(() => showLooki({ error: "unable to load Looki /moments" }));
});
