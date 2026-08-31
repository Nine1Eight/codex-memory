# AgentView Cloudflare Worker

This is a minimal API endpoint scaffold for Cloudflare Workers.

Endpoints:
- `GET /health`
- `GET /setup/status`
- `GET /looki/me`
- `GET /looki/moments`

Deploy with Wrangler after setting:
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `LOOKI_API_KEY`

The worker currently returns a static bootstrap status and is intended to be
extended or wired to D1/KV later.
