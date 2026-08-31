import { Pool } from "pg";
import { createApp, loadConfig } from "./src/app.js";

function main() {
  const config = loadConfig(process.env);
  const pool = new Pool({
    connectionString: config.databaseUrl,
    max: config.dbPoolMax,
    idleTimeoutMillis: config.dbIdleTimeoutMs,
    connectionTimeoutMillis: config.dbConnectionTimeoutMs
  });

  const app = createApp({ pool, config });
  const server = app.listen(config.port, () => {
    console.log(
      JSON.stringify({
        event: "server_started",
        service: "adtv",
        port: config.port,
        timeZone: config.timeZone,
        environment: config.nodeEnv
      })
    );
  });

  const shutdown = async (signal) => {
    console.log(JSON.stringify({ event: "shutdown_requested", signal }));
    server.close(async () => {
      try {
        await pool.end();
      } finally {
        process.exit(0);
      }
    });
  };

  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);

  process.on("unhandledRejection", (error) => {
    console.error(JSON.stringify({ event: "unhandled_rejection", error: String(error) }));
    process.exit(1);
  });

  process.on("uncaughtException", (error) => {
    console.error(JSON.stringify({ event: "uncaught_exception", error: String(error) }));
    process.exit(1);
  });
}

main();
