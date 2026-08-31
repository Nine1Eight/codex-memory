const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

function json(body, init = {}) {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: { ...JSON_HEADERS, ...(init.headers || {}) },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/health") {
      return json({ status: "ok" });
    }

    if (request.method === "GET" && url.pathname === "/setup/status") {
      return json({
        missing_categories: [],
        database_path: "cloudflare-workers-d1",
        environment: "production",
        public_url: env.PUBLIC_URL || url.origin,
        api_url: url.origin,
        database_mode: "d1",
        bootstrap_threshold: Number(env.BOOTSTRAP_THRESHOLD || "1000"),
        bootstrap: {
          count: Number(env.BOOTSTRAP_COUNT || "0"),
          threshold: Number(env.BOOTSTRAP_THRESHOLD || "1000"),
          locked: true,
        },
      });
    }

    if (request.method === "GET" && url.pathname === "/looki/me") {
      return proxyLooki(request, env, "/me");
    }

    if (request.method === "GET" && url.pathname === "/looki/moments") {
      const onDate = url.searchParams.get("on_date");
      const lookiPath = onDate ? `/moments?on_date=${encodeURIComponent(onDate)}` : "/moments";
      return proxyLooki(request, env, lookiPath);
    }

    return json(
      {
        error: "not_found",
        path: url.pathname,
      },
      { status: 404 }
    );
  },
};

async function proxyLooki(request, env, path) {
  const apiKey = env.LOOKI_API_KEY;
  if (!apiKey) {
    return json({ error: "looki_api_key_missing" }, { status: 503 });
  }

  const response = await fetch(`https://open.looki.ai/api/v1${path}`, {
    method: "GET",
    headers: {
      "X-API-Key": apiKey,
      accept: "application/json",
    },
  });

  const text = await response.text();
  return new Response(text, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") || "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}
