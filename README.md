# Codex Memory

Private source snapshot of local ARC, AI, security, GlyphMatics, and related projects.

## Layout

- `projects/` preserves each project's local relative path.
- Nested `.git` directories are intentionally omitted; this repository is the backup history.
- The snapshot includes committed files and useful uncommitted source files present on 2026-08-30.

## Included project groups

- ARC/AGI agents, RDL submissions, tools, harnesses, and local experiments
- Agent security framework and related security research
- GlyphMatics, SigilAGI, VIL, BrailleByte, training, and web projects
- AgentView, Genos, ADTV, Gladiator AI, Cohost, and related first-party projects
- Defendable-IP and biorefinery invention records

## Deliberate exclusions

To keep this repository safe and usable, the snapshot excludes credentials and environment
files, Git internals, dependency/vendor caches, virtual environments, generated logs and
build products, model weights, archives, APK/DMG binaries, PDF corpora, databases, and files
larger than 90 MB. Third-party upstream clones and deleted Trash contents are not mirrored.

The original local projects were not modified by this snapshot operation.

## Android ARC/Kaggle export

`android-local/arc-kaggle/` contains ARC- and Kaggle-named notebooks, scripts,
reports, bundles, and project directories discovered in Android shared storage.
Paths are preserved relative to shared storage. Embedded credentials are redacted
from the backup copy, and files at or above GitHub's per-file limit are omitted.

## Complete notebook export

`notebooks/termux-home/` and `notebooks/android-shared/` contain all active,
valid Jupyter notebooks discovered in Termux home and Android shared storage.
Paths are preserved relative to each source root. Credential-shaped literals are
redacted only in these exported copies. Trash, caches, environments, Android
app-private data, and malformed dependency test fixtures are excluded.
