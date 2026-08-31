function money(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2
  }).format(Number(value) || 0);
}

function number(value, digits = 2) {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  }).format(Number(value) || 0);
}

function html(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function metricCard(label, value, hint) {
  return `
    <article class="metric">
      <span>${html(label)}</span>
      <strong>${html(value)}</strong>
      <small>${html(hint || "")}</small>
    </article>
  `;
}

function setSummary(summary) {
  document.querySelector("#time-zone").textContent = summary.time_zone || "UTC";
  document.querySelector("#mode-label").textContent = summary.node_env || "production";

  const cards = [
    ["Users", summary.counts.users.toLocaleString(), "Registered accounts"],
    ["Advertisers", summary.counts.advertisers.toLocaleString(), "Active campaigns"],
    ["Open blocks", summary.counts.open_blocks.toLocaleString(), "Verification queue"],
    ["Today revenue", money(summary.finance.revenue_today), "Verified revenue"],
    ["User pool", money(summary.finance.user_pool_today), "55% settlement pool"],
    ["CU rate", number(summary.finance.cu_rate_today, 6), "USD per CU"]
  ];

  document.querySelector("#kpi-grid").innerHTML = cards.map((card) => metricCard(...card)).join("");
  document.querySelector("#summary-copy").textContent = [
    `As of ${summary.generated_at}`,
    `Last settlement date: ${summary.last_pool_date || "none"}`,
    `Verified blocks in window: ${summary.counts.verified_blocks_7d}`,
    `CU issued today: ${number(summary.finance.cu_issued_today, 2)}`
  ].join(" · ");
}

function renderBlocks(blocks) {
  if (!blocks.length) {
    return `<tr><td colspan="6" class="empty">No blocks available.</td></tr>`;
  }

  return blocks
    .map((block) => {
      const verified = Boolean(block.verified);
      return `
        <tr>
          <td>
            <div class="mono">${html(block.id)}</div>
            <div class="muted">${html(block.created_at || "")}</div>
          </td>
          <td>
            <div>${html(block.email || "Unknown user")}</div>
            <div class="muted">${html(block.wallet_address || "No wallet")}</div>
          </td>
          <td>${money(block.total_cpv)}</td>
          <td>${html(block.ad_slots)}</td>
          <td><span class="badge ${verified ? "success" : "warn"}">${verified ? "Verified" : "Open"}</span></td>
          <td>${
            verified
              ? '<span class="muted">Done</span>'
              : `<button class="inline" data-verify-block="${html(block.id)}">Verify</button>`
          }</td>
        </tr>
      `;
    })
    .join("");
}

function renderPools(pools) {
  if (!pools.length) {
    return `<tr><td colspan="4" class="empty">No settlement runs yet.</td></tr>`;
  }

  return pools
    .map(
      (pool) => `
        <tr>
          <td class="mono">${html(pool.pool_date)}</td>
          <td>${money(pool.total_revenue)}</td>
          <td>${money(pool.user_pool)}</td>
          <td class="mono">${number(pool.cu_rate, 6)}</td>
        </tr>
      `
    )
    .join("");
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "content-type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.message || "Request failed");
  }
  return payload;
}

async function loadSummary() {
  const summary = await requestJson("/api/summary");
  setSummary(summary);
  document.querySelector("#settlement-date").value = summary.date;
  return summary;
}

async function loadBlocks() {
  const { blocks } = await requestJson("/api/blocks?status=open&limit=25");
  document.querySelector("#blocks-table tbody").innerHTML = renderBlocks(blocks);
}

async function loadPools() {
  const { pools } = await requestJson("/api/pools?limit=10");
  document.querySelector("#pools-table tbody").innerHTML = renderPools(pools);
}

async function loadAll() {
  const status = document.querySelector("#settlement-result");
  status.textContent = "Refreshing.";
  try {
    await Promise.all([loadSummary(), loadBlocks(), loadPools()]);
    status.textContent = "Current.";
  } catch (error) {
    status.textContent = error.message;
  }
}

async function runSettlement(event) {
  event.preventDefault();
  const targetDate = document.querySelector("#settlement-date").value;
  const status = document.querySelector("#settlement-result");
  status.textContent = "Running settlement.";

  try {
    const result = await requestJson("/api/settlements/run", {
      method: "POST",
      body: JSON.stringify({ target_date: targetDate })
    });

    status.textContent = `Settled ${result.targetDate}: ${money(result.totalRevenue)} revenue, ${result.settlementsCreated} user settlements created.`;
    await Promise.all([loadSummary(), loadBlocks(), loadPools()]);
  } catch (error) {
    status.textContent = error.message;
  }
}

async function verifyBlock(blockId) {
  const status = document.querySelector("#settlement-result");
  status.textContent = `Verifying ${blockId}.`;

  try {
    const result = await requestJson(`/api/blocks/${blockId}/verify`, {
      method: "POST",
      body: JSON.stringify({})
    });

    status.textContent = `Block ${result.blockId} verified at ${money(result.totalCpv)} CPV.`;
    await Promise.all([loadSummary(), loadBlocks(), loadPools()]);
  } catch (error) {
    status.textContent = error.message;
  }
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-verify-block]");
  if (!button) {
    return;
  }
  verifyBlock(button.dataset.verifyBlock);
});

document.querySelector("#refresh-all").addEventListener("click", loadAll);
document.querySelector("#refresh-blocks").addEventListener("click", loadBlocks);
document.querySelector("#settlement-form").addEventListener("submit", runSettlement);

loadAll();
