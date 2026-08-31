# AgentView

AgentView is a protocol and platform for authorized semantic viewing, evidence-linked analysis, and cryptographically signed receipts.

## What AgentView Is

AgentView is a proof-of-understanding system for AI viewers.

YouTube measures whether a video played. AgentView measures whether an AI agent actually processed authorized content, understood it, and produced a verifiable result.

## How It Works

1. Receive authorized content
   - The system accepts owned, licensed, creator-authorized, public-domain, video, audio, captions, or transcripts.
2. Observe the content
   - The viewing agent processes speech and transcript, images and scene changes, on-screen text, event order, and relationships between claims, people, and objects.
3. Perform an objective
   - Examples include summarizing the video, answering questions, extracting instructions, identifying unsupported claims, comparing several videos, or evaluating which content provides the most useful knowledge.
4. Verify understanding
   - A separate verifier checks whether the agent’s conclusions are actually supported by timestamped evidence.
5. Score the view
   - The Viewing Confidence Score measures content coverage, evidence support, comprehension, internal consistency, and objective completion.
6. Issue a signed receipt
   - A Qualified Agent View receives a cryptographically signed record identifying the agent, content revision, objective, evidence, score, and verification result.

## Bot Versus AgentView

| Bot | Viewing agent |
| --- | --- |
| Starts playback | Processes meaning |
| Generates traffic | Generates knowledge |
| May repeat endlessly | Has a defined objective |
| Provides no comprehension proof | Produces evidence-linked results |
| Designed around platform counters | Produces a separate signed receipt |

## Example

An agent processes a ten-minute repair video. It identifies required tools, parts being replaced, each repair step, safety warnings, exact supporting timestamps, and any missing or contradictory instructions.

A verifier confirms the findings. The execution scores 91 and receives a signed Qualified Agent View receipt.

Replaying the same content with the same agent and objective does not create another unique Agent View. The system deduplicates it.

## What AgentView Ultimately Creates

AgentView creates a new analytics layer for machine intelligence:

- how many agents understood a video
- what information they extracted
- which videos teach agents most effectively
- which content contains reliable evidence
- which agents performed the best analysis
- whether an alleged AI view can be independently verified

An Agent View is not a YouTube view and does not inflate YouTube statistics. It is a separate measurement proving that an identifiable intelligence consumed and understood authorized content.

For the full component map and data pipeline, see [`docs/ARCHITECTURE.md`](/data/data/com.termux/files/home/agentview/docs/ARCHITECTURE.md).

## Current Status

- Milestone 0: repository bootstrap completed.
- Milestone 1: protocol core completed for canonical JSON, deduplication keys, Merkle roots, and scoring math.
- Milestone 2: tenant-scoped persistence and authority checks implemented in the in-process store.

## Verified Checks

- `python3 -m pytest -q apps/api/tests/test_setup_status.py`
- `python3 -m pytest -q packages/domain/tests/test_protocol.py apps/api/tests/test_setup_status.py`
- `python3 -m pytest -q packages/persistence/tests/test_store.py packages/domain/tests/test_protocol.py apps/api/tests/test_setup_status.py`
- `make verify`

## Notes

- The repository is still incomplete relative to the full spec, but the current codebase boots into a truthful setup-required state and enforces the first protocol and persistence invariants.
- The frontend lives in `apps/web` for GitHub Pages and `spaces/huggingface` for Hugging Face Spaces.
- Both frontend targets read `config.js` for the API base URL.
- `scripts/render_frontend_config.py` stamps the deploy-time API URL from secrets.
- The API endpoint scaffold lives in `cloudflare-worker/` for Cloudflare Workers.
