# Genos

Monorepository for the Genos platform, containing microservices and supporting components.

## Structure

- `api-orchestrator/` – API gateway / request router
- `core-engine/`      – Core business logic
- `llm-kernel/`       – LLM integration layer
- `image-renderer/`   – Image generation service
- `video-engine/`     – Video processing service
- `frontend/`         – Web frontend (static files or Next.js)
- `infra/`            – Infrastructure as code, deployment configs
- `tests/`            – Integration and end‑to‑end tests

Each service contains a minimal FastAPI scaffold and a Dockerfile.

## Getting Started

1. Clone the repository.
2. Navigate to a service directory.
3. Build and run with Docker:
   ```bash
   docker build -t genos-<service> .
   docker run -p 8000:8000 genos-<service>
