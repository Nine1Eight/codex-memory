const countNode = document.getElementById("count");
const thresholdNode = document.getElementById("threshold");
const lockStateNode = document.getElementById("lock-state");
const apiLabelNode = document.getElementById("api-label");
const statePillNode = document.getElementById("state-pill");
const apiBase = window.AGENTVIEW_API_BASE_URL || window.location.origin;
const defaultBootstrap = { count: 0, threshold: "?", locked: true };

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
