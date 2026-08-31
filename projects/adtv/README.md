# AdTV Mission Control

Production control surface for block verification, revenue tracking, and daily CU settlement.

## What this repo contains

- `server.js` starts the production service.
- `src/app.js` contains the Express app, auth, operational APIs, and settlement runner.
- `public/` contains the mission-control UI.
- `adtv_schema.sql` defines the database schema.
- `adtv_settlement.sql` defines the settlement function in SQL.
- `BUSINESS_MODEL.md` describes the commercial model and operating assumptions.
- `INVESTOR_ONE_PAGER.md` is the concise fundraising summary.

## Required environment

- `DATABASE_URL`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `PORT` optional, defaults to `3000`
- `APP_TIMEZONE` optional, defaults to `UTC`
- `TRUST_PROXY` optional, set to `true` behind a reverse proxy

## Run

```bash
npm install
npm start
```

## Container

```bash
docker build -t adtv .
docker run -p 3000:3000 \
  -e DATABASE_URL="postgresql://..." \
  -e ADMIN_USERNAME="admin" \
  -e ADMIN_PASSWORD="change-me" \
  adtv
```

## Test

```bash
npm test
```

## Endpoints

- `GET /health`
- `GET /ready`
- `GET /`
- `GET /api/summary`
- `GET /api/blocks`
- `GET /api/pools`
- `GET /api/activity`
- `POST /api/blocks/:blockId/verify`
- `POST /api/settlements/run`

## Deployment notes

- The control surface is protected with HTTP Basic Auth.
- Settlement is idempotent at the pool level and rewrites the day’s user-settlement rows.
- The app expects a PostgreSQL database with the tables defined in `adtv_schema.sql`.
