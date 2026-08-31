# Architecture

The framework is an offline state-machine laboratory. Scenarios are immutable,
strictly validated inputs. `Simulator.transition` is the only state mutation
boundary and all tools are in-process recorders. The mock-tool module imports
neither networking nor subprocess facilities.

```text
scenario -> generator -> search -> simulator -> oracle -> causality
                                      |                     |
                                      +-> replay/minimize <--+
                                                |
                                      report/submission gate
```

Canonical JSON and SHA-256 identify scenarios, states, reports, and replay
packages. Every action carries provenance. The failure oracle matches structured
events and typed conditions; keywords alone cannot create a finding.

## House of Mirrors mapping

The supplied GlyphMatics design is represented only as a synthetic benchmark
fixture. Mirror files exist in the virtual filesystem, authority is a simulated
permission set, honeyglyphs are inert strings, and observation is an event log.
There is no production overlay, real identity decision, credential revocation,
network containment, cryptography, or external tracking.

The conceptual components map as follows:

- Semantic Firewall and Trust Membrane: strict scenario/action validation.
- Provenance Lattice and taint tracking: artifact and event provenance.
- Authority Tokens and Intent Lock: declared permissions, tools, and budgets.
- Context Quarantine: untrusted content remains data attached to provenance.
- Mirror Overlay: session-specific synthetic virtual state.
- Honeyglyphs: inert fixture identifiers.
- Meaning Hash: canonical structural and state hashes.

## Safety invariants

The runtime never invokes shell text, browsers, APIs, databases, email, or
messaging services. It reads only paths explicitly passed to the CLI and writes
only explicit output paths. Evaluation has no plugin loading and no dynamic
imports from scenarios. Unknown capabilities fail closed.
