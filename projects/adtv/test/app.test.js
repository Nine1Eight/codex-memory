import assert from "node:assert/strict";
import test from "node:test";
import http from "node:http";
import { createApp, loadConfig, settlementRun } from "../src/app.js";

class FakePool {
  constructor() {
    this.state = {
      blocks: [
        {
          id: "block-1",
          user_id: "user-1",
          total_cpv: "1.25",
          verified: false,
          created_at: new Date("2026-08-25T15:00:00Z")
        }
      ],
      users: [{ id: "user-1" }],
      advertisers: [{ id: "adv-1" }],
      creatives: [{ id: "creative-1" }],
      revenueEvents: [{ cpv: "10.00", verified: true, created_at: new Date("2026-08-25T10:00:00Z") }],
      cuTransactions: [{ cu_amount: "200", created_at: new Date("2026-08-25T10:00:00Z"), user_id: "user-1" }],
      pools: [],
      settlements: []
    };
    this.lastInsertedSettlement = null;
    this.connect = this.connect.bind(this);
    this.release = this.release.bind(this);
  }

  async connect() {
    return this;
  }

  release() {}

  async query(sql, params = []) {
    const normalized = sql.replaceAll(/\s+/g, " ").trim();
    if (normalized === "SELECT 1 AS ready") {
      return { rows: [{ ready: 1 }] };
    }
    if (normalized.startsWith("SELECT COUNT(*)::int AS value FROM users")) {
      return { rows: [{ value: this.state.users.length }] };
    }
    if (normalized.startsWith("SELECT COUNT(*)::int AS value FROM advertisers")) {
      return { rows: [{ value: this.state.advertisers.length }] };
    }
    if (normalized.startsWith("SELECT COUNT(*)::int AS value FROM creatives")) {
      return { rows: [{ value: this.state.creatives.length }] };
    }
    if (normalized.startsWith("SELECT COUNT(*)::int AS value FROM blocks WHERE verified = FALSE")) {
      return { rows: [{ value: this.state.blocks.filter((block) => !block.verified).length }] };
    }
    if (normalized.includes("FROM blocks WHERE verified = TRUE")) {
      return { rows: [{ value: 0 }] };
    }
    if (normalized.includes("FROM revenue_events WHERE verified = TRUE")) {
      const total = this.state.revenueEvents.reduce((sum, row) => sum + Number(row.cpv), 0);
      if (normalized.includes("AS total_rev")) {
        return { rows: [{ total_rev: total }] };
      }
      return { rows: [{ value: total }] };
    }
    if (normalized.includes("FROM cu_transactions WHERE DATE(created_at) = $1")) {
      const total = this.state.cuTransactions.reduce((sum, row) => sum + Number(row.cu_amount), 0);
      if (normalized.includes("AS total_cu")) {
        return { rows: [{ total_cu: total }] };
      }
      return { rows: [{ value: total }] };
    }
    if (normalized.startsWith("SELECT COALESCE(total_revenue, 0) AS total_revenue")) {
      return { rows: [{ total_revenue: 10, platform_share: 4.5, user_pool: 5.5, total_cu: 200, cu_rate: 0.0275 }] };
    }
    if (normalized.startsWith("SELECT pool_date, total_revenue, platform_share, user_pool, total_cu, cu_rate FROM daily_revenue_pools")) {
      return { rows: this.state.pools.slice(0, params[0] ?? 10) };
    }
    if (normalized.startsWith("SELECT pool_date, total_revenue, platform_share, user_pool, total_cu, cu_rate, created_at FROM daily_revenue_pools")) {
      return { rows: this.state.pools.slice(0, params[0] ?? 10) };
    }
    if (normalized.startsWith("SELECT b.id, b.user_id, b.total_cpv, b.verified, b.created_at,")) {
      return {
        rows: this.state.blocks.map((block) => ({
          ...block,
          email: "tester@example.com",
          wallet_address: "0xabc",
          ad_slots: 2,
          cu_issued: Number(block.total_cpv) * 100
        }))
      };
    }
    if (normalized === "BEGIN" || normalized === "COMMIT" || normalized === "ROLLBACK") {
      return { rows: [] };
    }
    if (normalized.startsWith("SELECT id, user_id, total_cpv, verified FROM blocks WHERE id = $1 FOR UPDATE")) {
      return { rows: [this.state.blocks[0]] };
    }
    if (normalized.startsWith("UPDATE blocks SET verified = TRUE, total_cpv = $2 WHERE id = $1")) {
      this.state.blocks[0] = {
        ...this.state.blocks[0],
        verified: true,
        total_cpv: params[1]
      };
      return { rows: [] };
    }
    if (normalized.startsWith("INSERT INTO revenue_events(block_id, advertiser_id, cpv, verified)")) {
      this.state.revenueEvents.push({ cpv: String(params[2]), verified: true });
      return { rows: [] };
    }
    if (normalized.startsWith("INSERT INTO cu_transactions(user_id, block_id, cu_amount)")) {
      this.state.cuTransactions.push({ user_id: params[0], block_id: params[1], cu_amount: String(params[2]) });
      return { rows: [] };
    }
    if (normalized.startsWith("DELETE FROM user_settlements WHERE pool_date = $1")) {
      this.state.settlements = this.state.settlements.filter((row) => row.pool_date !== params[0]);
      return { rows: [] };
    }
    if (normalized.startsWith("INSERT INTO daily_revenue_pools(")) {
      const row = {
        pool_date: params[0],
        total_revenue: params[1],
        platform_share: params[2],
        user_pool: params[3],
        total_cu: params[4],
        cu_rate: params[5]
      };
      this.state.pools = [row];
      return { rows: [row] };
    }
    if (normalized.startsWith("INSERT INTO user_settlements(pool_date, user_id, cu_earned, usd_allocated)")) {
      this.state.settlements.push({ pool_date: params[0], user_id: "user-1", cu_earned: 200, usd_allocated: 5.5 });
      return { rowCount: 1, rows: [] };
    }

    throw new Error(`Unhandled SQL: ${normalized}`);
  }
}

function buildConfig(overrides = {}) {
  return {
    nodeEnv: "test",
    port: 0,
    databaseUrl: "postgresql://example.invalid/test",
    adminUsername: "admin",
    adminPassword: "secret",
    timeZone: "UTC",
    dbPoolMax: 2,
    dbIdleTimeoutMs: 1000,
    dbConnectionTimeoutMs: 1000,
    bodyLimit: "256kb",
    trustProxy: false,
    ...overrides
  };
}

function withServer(app, fn) {
  return new Promise((resolve, reject) => {
    const server = http.createServer(app);
    server.listen(0, async () => {
      const { port } = server.address();
      try {
        const value = await fn(`http://127.0.0.1:${port}`);
        server.close((closeError) => (closeError ? reject(closeError) : resolve(value)));
      } catch (error) {
        server.close(() => reject(error));
      }
    });
  });
}

function authHeader() {
  return `Basic ${Buffer.from("admin:secret").toString("base64")}`;
}

test("loadConfig validates deployment settings", () => {
  assert.throws(() => loadConfig({}), /DATABASE_URL/);
  assert.throws(
    () =>
      loadConfig({
        DATABASE_URL: "postgresql://localhost/test",
        ADMIN_USERNAME: "admin"
      }),
    /ADMIN_USERNAME and ADMIN_PASSWORD/
  );
});

test("mission control responds with summary and control surfaces", async () => {
  const pool = new FakePool();
  const app = createApp({ pool, config: buildConfig() });

  await withServer(app, async (baseUrl) => {
    const health = await fetch(`${baseUrl}/health`);
    assert.equal(health.status, 200);

    const summaryRes = await fetch(`${baseUrl}/api/summary`, {
      headers: { authorization: authHeader() }
    });
    assert.equal(summaryRes.status, 200);
    const summary = await summaryRes.json();
    assert.equal(summary.counts.users, 1);
    assert.equal(summary.finance.revenue_today, 10);

    const blocksRes = await fetch(`${baseUrl}/api/blocks?status=open`, {
      headers: { authorization: authHeader() }
    });
    assert.equal(blocksRes.status, 200);
    const blocks = await blocksRes.json();
    assert.equal(blocks.blocks.length, 1);
  });
});

test("verify and settlement routes write the expected records", async () => {
  const pool = new FakePool();
  const app = createApp({ pool, config: buildConfig() });

  await withServer(app, async (baseUrl) => {
    const verifyRes = await fetch(`${baseUrl}/api/blocks/block-1/verify`, {
      method: "POST",
      headers: {
        authorization: authHeader(),
        "content-type": "application/json"
      },
      body: JSON.stringify({ total_cpv: 2.5 })
    });

    assert.equal(verifyRes.status, 200);
    const verified = await verifyRes.json();
    assert.equal(verified.status, "verified");

    const settleRes = await fetch(`${baseUrl}/api/settlements/run`, {
      method: "POST",
      headers: {
        authorization: authHeader(),
        "content-type": "application/json"
      },
      body: JSON.stringify({ target_date: "2026-08-25" })
    });

    assert.equal(settleRes.status, 200);
    const settled = await settleRes.json();
    assert.equal(settled.status, "settled");
    assert.equal(settled.targetDate, "2026-08-25");
  });
});

test("settlement helper can run standalone", async () => {
  const pool = new FakePool();
  const result = await settlementRun(pool, "2026-08-25");
  assert.equal(result.targetDate, "2026-08-25");
  assert.equal(result.totalRevenue, 10);
});
