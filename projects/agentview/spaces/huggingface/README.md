---
title: AgentView
emoji: 👁️
colorFrom: slate
colorTo: cyan
sdk: static
app_file: index.html
---

# AgentView Space

This Space reuses the same static frontend layout as `apps/web` with a slightly richer
presentation for demos and previews.

Update `config.js` during deployment to point at the live AgentView API.
The repo includes `scripts/render_frontend_config.py` so deploy steps can stamp the URL
from `AGENTVIEW_HF_API_BASE_URL`.
