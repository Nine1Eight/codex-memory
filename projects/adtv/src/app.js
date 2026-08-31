import crypto from "node:crypto";
import express from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const publicDir = path.join(projectRoot, "public");

class HttpError extends Error {
  constructor(statusCode, message, details = undefined) {
    super(message);
    this.name = "HttpError";
    this.statusCode = statusCode;
    this.details = details;
  }
}

function asNumber(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function asInteger(value, fallback = 0) {
  const parsed = Number.parseInt(String(value), 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function clampInt(value, min, max, fallback) {
  const parsed = asInteger(value, fallback);
  return Math.min(max, Math.max(min, parsed));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function datePartsInTimeZone(date, timeZone) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).formatToParts(date);

  const year = parts.find((part) => part.type === "year")?.value ?? "1970";
  const month = parts.find((part) => part.type === "month")?.value ?? "01";
  const day = parts.find((part) => part.type === "day")?.value ?? "01";
  return `${year}-${month}-${day}`;
}

function parseYmd(value) {
  if (typeof value !== "string") {
    return null;
  }

  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return null;
  }

  return value;
}

function formatMoney(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2
  }).format(asNumber(value));
}

function formatDecimal(value, digits = 2) {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  }).format(asNumber(value));
}

function toIso(value) {
  if (!value) {
    return null;
  }
  if (value instanceof Date) {
    return value.toISOString();
  }
  return String(value);
}

function readBasicAuth(header) {
  if (!header || !header.startsWith("Basic ")) {
    return null;
  }

  try {
    const decoded = Buffer.from(header.slice(6), "base64").toString("utf8");
    const separatorIndex = decoded.indexOf(":");
    if (separatorIndex < 0) {
      return null;
    }

    return {
      username: decoded.slice(0, separatorIndex),
      password: decoded.slice(separatorIndex + 1)
    };
  } catch {
    return null;
  }
}

function sendAuthChallenge(res) {
  res.setHeader("WWW-Authenticate", 'Basic realm="AdTV Mission Control", charset="UTF-8"');
  res.status(401).json({
    error: "authentication_required",
    message: "Basic authentication is required."
  });
}

function requireAuth(config) {
  return (req, res, next) => {
    if (req.path === "/health" || req.path === "/ready") {
      return next();
    }

    const credentials = readBasicAuth(req.headers.authorization);
    if (!credentials) {
      return sendAuthChallenge(res);
    }

    if (
      credentials.username !== config.adminUsername ||
      credentials.password !== config.adminPassword
    ) {
      return sendAuthChallenge(res);
    }

    req.authUser = credentials.username;
    return next();
  };
}

function requestLogger() {
  return (req, res, next) => {
    const requestId = crypto.randomUUID();
    const startedAt = process.hrtime.bigint();

    req.requestId = requestId;
    res.setHeader("x-request-id", requestId);

    res.on("finish", () => {
      const elapsedMs = Number(process.hrtime.bigint() - startedAt) / 1_000_000;
      console.log(
        JSON.stringify({
          event: "request",
          requestId,
          method: req.method,
          path: req.originalUrl,
          status: res.statusCode,
          elapsedMs: Number(elapsedMs.toFixed(2))
        })
      );
    });

    next();
  };
}

async function tx(pool, fn) {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const result = await fn(client);
    await client.query("COMMIT");
    return result;
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

async function settlementRun(pool, targetDate) {
  return tx(pool, async (client) => {
    const revenueResult = await client.query(
      `SELECT COALESCE(SUM(cpv), 0) AS total_rev
       FROM revenue_events
       WHERE verified = TRUE
         AND DATE(created_at) = $1`,
      [targetDate]
    );

    const cuResult = await client.query(
      `SELECT COALESCE(SUM(cu_amount), 0) AS total_cu
       FROM cu_transactions
       WHERE DATE(created_at) = $1`,
      [targetDate]
    );

    const totalRevenue = asNumber(revenueResult.rows[0]?.total_rev);
    const totalCu = asNumber(cuResult.rows[0]?.total_cu);
    const platformShare = totalRevenue * 0.45;
    const userPool = totalRevenue * 0.55;
    const cuRate = totalCu > 0 ? userPool / totalCu : 0;

    await client.query(
      `INSERT INTO daily_revenue_pools(
         pool_date,
         total_revenue,
         platform_share,
         user_pool,
         total_cu,
         cu_rate
       )
       VALUES ($1, $2, $3, $4, $5, $6)
       ON CONFLICT (pool_date) DO UPDATE SET
         total_revenue = EXCLUDED.total_revenue,
         platform_share = EXCLUDED.platform_share,
         user_pool = EXCLUDED.user_pool,
        total_cu = EXCLUDED.total_cu,
        cu_rate = EXCLUDED.cu_rate`,
      [targetDate, totalRevenue, platformShare, userPool, totalCu, cuRate]
    );

    await client.query("DELETE FROM user_settlements WHERE pool_date = $1", [targetDate]);

    const settlementResult = await client.query(
      `INSERT INTO user_settlements(pool_date, user_id, cu_earned, usd_allocated)
       SELECT
         $1,
         user_id,
         SUM(cu_amount),
         SUM(cu_amount) * $2
       FROM cu_transactions
       WHERE DATE(created_at) = $1
       GROUP BY user_id`,
      [targetDate, cuRate]
    );

    return {
      targetDate,
      totalRevenue,
      platformShare,
      userPool,
      totalCu,
      cuRate,
      settlementsCreated: settlementResult.rowCount
    };
  });
}

function invalid(message, details = undefined) {
  return new HttpError(400, message, details);
}

async function querySingle(pool, sql, params = []) {
  const { rows } = await pool.query(sql, params);
  return rows[0] ?? null;
}

function createErrorPayload(error, requestId) {
  if (error instanceof HttpError) {
    return {
      statusCode: error.statusCode,
      body: {
        error: error.name,
        message: error.message,
        requestId,
        details: error.details ?? null
      }
    };
  }

  return {
    statusCode: 500,
    body: {
      error: "internal_server_error",
      message: "The request could not be completed.",
      requestId
    }
  };
}

export function loadConfig(env) {
  const databaseUrl = env.DATABASE_URL;
  if (!databaseUrl) {
    throw new Error("DATABASE_URL is required.");
  }

  try {
    // Validate that the URL is structurally sound before starting the pool.
    new URL(databaseUrl);
  } catch {
    throw new Error("DATABASE_URL must be a valid connection URL.");
  }

  const adminUsername = env.ADMIN_USERNAME;
  const adminPassword = env.ADMIN_PASSWORD;
  if (!adminUsername || !adminPassword) {
    throw new Error("ADMIN_USERNAME and ADMIN_PASSWORD are required.");
  }

  return {
    nodeEnv: env.NODE_ENV ?? "production",
    port: clampInt(env.PORT ?? "3000", 1, 65535, 3000),
    databaseUrl,
    adminUsername,
    adminPassword,
    timeZone: env.APP_TIMEZONE || "UTC",
    dbPoolMax: clampInt(env.DB_POOL_MAX ?? "10", 1, 50, 10),
    dbIdleTimeoutMs: clampInt(env.DB_IDLE_TIMEOUT_MS ?? "10000", 1000, 120000, 10000),
    dbConnectionTimeoutMs: clampInt(env.DB_CONNECTION_TIMEOUT_MS ?? "5000", 1000, 30000, 5000),
    bodyLimit: env.BODY_LIMIT ?? "256kb",
    trustProxy: env.TRUST_PROXY === "true"
  };
}

function renderPage(config) {
  const title = "AdTV Mission Control";
  const timeZone = escapeHtml(config.timeZone);
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="theme-color" content="#07111f" />
  <title>${title}</title>
  <link rel="stylesheet" href="/assets/styles.css" />
</head>
<body>
  <div class="backdrop"></div>
  <main class="shell">
    <header class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Production Control Surface</p>
        <h1>${title}</h1>
        <p class="lede">
          Deployment console for block verification, revenue settlement, and daily operations.
        </p>
      </div>
      <div class="hero-meta">
        <div class="meta-card">
          <span>Timezone</span>
          <strong>${timeZone}</strong>
        </div>
        <div class="meta-card">
          <span>Mode</span>
          <strong>${escapeHtml(config.nodeEnv)}</strong>
        </div>
      </div>
    </header>

    <section class="grid kpis" id="kpi-grid"></section>

    <section class="grid two-up">
      <article class="panel">
        <div class="panel-head">
          <div>
            <p class="panel-label">Verification Queue</p>
            <h2>Open Blocks</h2>
          </div>
          <button class="ghost" id="refresh-blocks">Refresh</button>
        </div>
        <div class="table-wrap">
          <table class="table" id="blocks-table">
            <thead>
              <tr>
                <th>Block</th>
                <th>User</th>
                <th>CPV</th>
                <th>Ads</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <div>
            <p class="panel-label">Settlement Runner</p>
            <h2>Daily Close</h2>
          </div>
        </div>
        <form id="settlement-form" class="stack">
          <label>
            <span>Target date</span>
            <input type="date" name="target_date" id="settlement-date" />
          </label>
          <button type="submit" class="primary">Run settlement</button>
        </form>
        <div class="callout" id="settlement-result">
          Ready.
        </div>
        <div class="subpanel">
          <h3>Recent Pools</h3>
          <div class="table-wrap small">
            <table class="table" id="pools-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Revenue</th>
                  <th>User Pool</th>
                  <th>Rate</th>
                </tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
        </div>
      </article>
    </section>

    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="panel-label">Operational Snapshot</p>
          <h2>System Summary</h2>
        </div>
        <button class="ghost" id="refresh-all">Refresh All</button>
      </div>
      <div class="summary-copy" id="summary-copy">Loading summary.</div>
    </section>
  </main>
  <script>
    window.__ADTV_TIME_ZONE__ = ${JSON.stringify(config.timeZone)};
  </script>
  <script src="/assets/app.js" type="module"></script>
</body>
</html>`;
}

function renderMetricCard(metric) {
  return `
    <article class="metric">
      <span>${escapeHtml(metric.label)}</span>
      <strong>${escapeHtml(metric.value)}</strong>
      <small>${escapeHtml(metric.hint ?? "")}</small>
    </article>
  `;
}

function renderBlocks(blocks) {
  if (!blocks.length) {
    return `<tr><td colspan="6" class="empty">No blocks available.</td></tr>`;
  }

  return blocks
    .map((block) => {
      const badgeClass = block.verified ? "badge success" : "badge warn";
      const badgeText = block.verified ? "Verified" : "Open";
      const action = block.verified
        ? `<span class="muted">Done</span>`
        : `<button class="inline" data-verify-block="${escapeHtml(block.id)}">Verify</button>`;
      return `
        <tr>
          <td>
            <div class="mono">${escapeHtml(block.id)}</div>
            <div class="muted">${escapeHtml(block.created_at ?? "")}</div>
          </td>
          <td>
            <div>${escapeHtml(block.email ?? "Unknown user")}</div>
            <div class="muted">${escapeHtml(block.wallet_address ?? "No wallet")}</div>
          </td>
          <td>${formatMoney(block.total_cpv ?? 0)}</td>
          <td>${escapeHtml(String(block.ad_slots ?? 0))}</td>
          <td><span class="${badgeClass}">${badgeText}</span></td>
          <td>${action}</td>
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
          <td class="mono">${escapeHtml(pool.pool_date)}</td>
          <td>${formatMoney(pool.total_revenue)}</td>
          <td>${formatMoney(pool.user_pool)}</td>
          <td class="mono">${formatDecimal(pool.cu_rate, 6)}</td>
        </tr>
      `
    )
    .join("");
}

function renderSummary(summary) {
  const cards = [
    {
      label: "Users",
      value: summary.counts.users.toLocaleString(),
      hint: "Registered accounts"
    },
    {
      label: "Advertisers",
      value: summary.counts.advertisers.toLocaleString(),
      hint: "Active campaigns"
    },
    {
      label: "Open blocks",
      value: summary.counts.open_blocks.toLocaleString(),
      hint: "Verification queue"
    },
    {
      label: "Today revenue",
      value: formatMoney(summary.finance.revenue_today),
      hint: "Verified revenue"
    },
    {
      label: "User pool",
      value: formatMoney(summary.finance.user_pool_today),
      hint: "55% settlement pool"
    },
    {
      label: "CU rate",
      value: formatDecimal(summary.finance.cu_rate_today, 6),
      hint: "USD per CU"
    }
  ];

  return cards.map(renderMetricCard).join("");
}

function renderSummaryCopy(summary) {
  return [
    `As of ${summary.generated_at}`,
    `Last settlement date: ${summary.last_pool_date ?? "none"}`,
    `Verified blocks in window: ${summary.counts.verified_blocks_7d}`,
    `CU issued today: ${formatDecimal(summary.finance.cu_issued_today, 2)}`
  ].join(" · ");
}

async function getSummary(pool, config) {
  const today = datePartsInTimeZone(new Date(), config.timeZone);
  const [
    users,
    advertisers,
    creatives,
    openBlocks,
    verifiedBlocks7d,
    revenueToday,
    cuIssuedToday,
    poolToday,
    latestPool
  ] = await Promise.all([
    querySingle(pool, "SELECT COUNT(*)::int AS value FROM users"),
    querySingle(pool, "SELECT COUNT(*)::int AS value FROM advertisers WHERE status = 'active'"),
    querySingle(pool, "SELECT COUNT(*)::int AS value FROM creatives WHERE status = 'active'"),
    querySingle(pool, "SELECT COUNT(*)::int AS value FROM blocks WHERE verified = FALSE"),
    querySingle(
      pool,
      `SELECT COUNT(*)::int AS value
       FROM blocks
       WHERE verified = TRUE
         AND created_at >= CURRENT_DATE - INTERVAL '7 days'`
    ),
    querySingle(
      pool,
      `SELECT COALESCE(SUM(cpv), 0) AS value
       FROM revenue_events
       WHERE verified = TRUE
         AND DATE(created_at) = $1`,
      [today]
    ),
    querySingle(
      pool,
      `SELECT COALESCE(SUM(cu_amount), 0) AS value
       FROM cu_transactions
       WHERE DATE(created_at) = $1`,
      [today]
    ),
    querySingle(
      pool,
      `SELECT COALESCE(total_revenue, 0) AS total_revenue,
              COALESCE(platform_share, 0) AS platform_share,
              COALESCE(user_pool, 0) AS user_pool,
              COALESCE(total_cu, 0) AS total_cu,
              COALESCE(cu_rate, 0) AS cu_rate
       FROM daily_revenue_pools
       WHERE pool_date = $1`,
      [today]
    ),
    querySingle(
      pool,
      `SELECT pool_date, total_revenue, platform_share, user_pool, total_cu, cu_rate
       FROM daily_revenue_pools
       ORDER BY pool_date DESC
       LIMIT 1`
    )
  ]);

  return {
    service: "adtv",
    node_env: config.nodeEnv,
    generated_at: new Date().toISOString(),
    time_zone: config.timeZone,
    date: today,
    counts: {
      users: asInteger(users?.value),
      advertisers: asInteger(advertisers?.value),
      creatives: asInteger(creatives?.value),
      open_blocks: asInteger(openBlocks?.value),
      verified_blocks_7d: asInteger(verifiedBlocks7d?.value)
    },
    finance: {
      revenue_today: asNumber(revenueToday?.value),
      cu_issued_today: asNumber(cuIssuedToday?.value),
      user_pool_today: asNumber(poolToday?.user_pool),
      platform_share_today: asNumber(poolToday?.platform_share),
      total_cu_today: asNumber(poolToday?.total_cu),
      cu_rate_today: asNumber(poolToday?.cu_rate)
    },
    last_pool_date: latestPool?.pool_date ?? null
  };
}

async function getBlocks(pool, limit = 20, verified = null) {
  const params = [limit];
  let where = "TRUE";

  if (verified === true) {
    where = "b.verified = TRUE";
  } else if (verified === false) {
    where = "b.verified = FALSE";
  }

  const { rows } = await pool.query(
    `SELECT
       b.id,
       b.user_id,
       b.total_cpv,
       b.verified,
       b.created_at,
       u.email,
       u.wallet_address,
       COALESCE(ad.slot_count, 0) AS ad_slots,
       COALESCE(cu.total_cu, 0) AS cu_issued
     FROM blocks b
     LEFT JOIN users u ON u.id = b.user_id
     LEFT JOIN LATERAL (
       SELECT COUNT(*)::int AS slot_count
       FROM block_ads ba
       WHERE ba.block_id = b.id
     ) ad ON TRUE
     LEFT JOIN LATERAL (
       SELECT COALESCE(SUM(cu_amount), 0) AS total_cu
       FROM cu_transactions ct
       WHERE ct.block_id = b.id
     ) cu ON TRUE
     WHERE ${where}
     ORDER BY b.created_at DESC
     LIMIT $1`,
    params
  );

  return rows.map((row) => ({
    ...row,
    total_cpv: asNumber(row.total_cpv),
    ad_slots: asInteger(row.ad_slots),
    cu_issued: asNumber(row.cu_issued),
    created_at: toIso(row.created_at)
  }));
}

async function getPools(pool, limit = 10) {
  const { rows } = await pool.query(
    `SELECT pool_date, total_revenue, platform_share, user_pool, total_cu, cu_rate, created_at
     FROM daily_revenue_pools
     ORDER BY pool_date DESC
     LIMIT $1`,
    [limit]
  );

  return rows.map((row) => ({
    ...row,
    total_revenue: asNumber(row.total_revenue),
    platform_share: asNumber(row.platform_share),
    user_pool: asNumber(row.user_pool),
    total_cu: asNumber(row.total_cu),
    cu_rate: asNumber(row.cu_rate),
    created_at: toIso(row.created_at)
  }));
}

export function createApp({ pool, config }) {
  const app = express();
  app.disable("x-powered-by");
  if (config.trustProxy) {
    app.set("trust proxy", 1);
  }

  app.use(requestLogger());
  app.use(express.json({ limit: config.bodyLimit }));
  app.use(express.urlencoded({ extended: false }));

  app.get("/health", (req, res) => {
    res.json({
      status: "ok",
      service: "adtv",
      requestId: req.requestId,
      timeZone: config.timeZone,
      now: new Date().toISOString()
    });
  });

  app.get("/ready", async (req, res, next) => {
    try {
      await pool.query("SELECT 1 AS ready");
      res.json({
        status: "ready",
        service: "adtv",
        requestId: req.requestId
      });
    } catch (error) {
      next(error);
    }
  });

  app.use(requireAuth(config));

  app.use("/assets", express.static(publicDir, { etag: true, maxAge: "1h" }));

  app.get("/", (req, res) => {
    res.type("html").send(renderPage(config));
  });

  app.get("/api/summary", async (req, res, next) => {
    try {
      const summary = await getSummary(pool, config);
      res.json(summary);
    } catch (error) {
      next(error);
    }
  });

  app.get("/api/blocks", async (req, res, next) => {
    try {
      const limit = clampInt(req.query.limit ?? "20", 1, 100, 20);
      const status = (req.query.status ?? "open").toString().toLowerCase();
      const verified = status === "verified" ? true : status === "all" ? null : false;
      const blocks = await getBlocks(pool, limit, verified);
      res.json({ blocks });
    } catch (error) {
      next(error);
    }
  });

  app.get("/api/pools", async (req, res, next) => {
    try {
      const limit = clampInt(req.query.limit ?? "10", 1, 50, 10);
      const pools = await getPools(pool, limit);
      res.json({ pools });
    } catch (error) {
      next(error);
    }
  });

  app.get("/api/activity", async (req, res, next) => {
    try {
      const limit = clampInt(req.query.limit ?? "20", 1, 50, 20);
      const { rows } = await pool.query(
        `SELECT
           'revenue_event' AS kind,
           id,
           block_id,
           advertiser_id,
           cpv,
           verified,
           created_at
         FROM revenue_events
         ORDER BY created_at DESC
         LIMIT $1`,
        [limit]
      );

      res.json({
        activity: rows.map((row) => ({
          ...row,
          cpv: asNumber(row.cpv),
          created_at: toIso(row.created_at)
        }))
      });
    } catch (error) {
      next(error);
    }
  });

  app.post("/api/blocks/:blockId/verify", async (req, res, next) => {
    const blockId = req.params.blockId;
    try {
      const result = await tx(pool, async (client) => {
        const block = await querySingle(
          client,
          `SELECT id, user_id, total_cpv, verified
           FROM blocks
           WHERE id = $1
           FOR UPDATE`,
          [blockId]
        );

        if (!block) {
          throw invalid("Block not found.");
        }

        if (block.verified) {
          throw new HttpError(409, "Block is already verified.");
        }

        const requestedCpv = req.body?.total_cpv;
        const totalCpv = requestedCpv !== undefined ? asNumber(requestedCpv, NaN) : asNumber(block.total_cpv);
        if (!Number.isFinite(totalCpv) || totalCpv <= 0) {
          throw invalid("A positive total_cpv is required to verify the block.");
        }

        if (!block.user_id) {
          throw invalid("The block is missing a user_id and cannot be verified.");
        }

        await client.query(
          `UPDATE blocks
           SET verified = TRUE,
               total_cpv = $2
           WHERE id = $1`,
          [blockId, totalCpv]
        );

        await client.query(
          `INSERT INTO revenue_events(block_id, advertiser_id, cpv, verified)
           VALUES ($1, $2, $3, TRUE)`,
          [blockId, null, totalCpv]
        );

        const cuAmount = totalCpv * 100;
        await client.query(
          `INSERT INTO cu_transactions(user_id, block_id, cu_amount)
           VALUES ($1, $2, $3)`,
          [block.user_id, blockId, cuAmount]
        );

        return {
          blockId,
          userId: block.user_id,
          totalCpv,
          cuAmount
        };
      });

      res.json({
        status: "verified",
        ...result
      });
    } catch (error) {
      next(error);
    }
  });

  app.post("/api/settlements/run", async (req, res, next) => {
    try {
      const targetDate = parseYmd(req.body?.target_date) ?? datePartsInTimeZone(new Date(), config.timeZone);
      const result = await settlementRun(pool, targetDate);
      res.json({
        status: "settled",
        ...result
      });
    } catch (error) {
      next(error);
    }
  });

  app.use((req, res, next) => {
    next(new HttpError(404, `No route matches ${req.method} ${req.path}.`));
  });

  app.use((error, req, res, next) => {
    const payload = createErrorPayload(error, req.requestId);
    if (payload.statusCode >= 500) {
      console.error(
        JSON.stringify({
          event: "request_error",
          requestId: req.requestId,
          method: req.method,
          path: req.originalUrl,
          error: String(error?.stack ?? error)
        })
      );
    }

    res.status(payload.statusCode).json(payload.body);
  });

  return app;
}

export {
  HttpError,
  asNumber,
  asInteger,
  clampInt,
  datePartsInTimeZone,
  formatDecimal,
  formatMoney,
  parseYmd,
  renderBlocks,
  renderPools,
  renderSummary,
  renderSummaryCopy,
  settlementRun
};
