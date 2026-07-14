# Risk, Permissions, and Evidence

## Risk model

Risk grows with irreversibility, external effects, sensitive access, authority ambiguity, and weak evidence. Contract permissions to the smallest reversible surface that can deliver the outcome.

## Permission model

List allowed and prohibited actions explicitly. Repository write access does not grant runtime, provider/API, broker/account, data/DB, secret, state, deployment, merge, or release authority. If completion needs new authority, stop and escalate.

## Trust model

State what is authoritative, what is generated, what may be stale, and what cannot prove acceptance. Fail closed when identity, provenance, currency, completeness, or permission is uncertain.

## Evidence quality

Evidence records the exact repository/ref, changed files, commands, results, failures, skipped checks, artifacts, and remaining unknowns. Evidence must be reproducible, scoped, secret-safe, and linked to the contract. Generated output and test success support claims; they do not make product decisions or guarantee real-world outcomes.

## Stop conditions

Stop on permission uncertainty, unexpected mutation, secret exposure risk, authority conflict, failed frozen acceptance, unverifiable provenance, external-state mismatch, or pressure to conceal weakened controls. Preserve state and report the shortest accurate blocker.
