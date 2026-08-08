# Script authority and safety

These scripts are retained for reproducibility and historical evidence. Their
presence is not permission to execute them.

Current controls:

- acquisition scripts are stopped unless a separately authorised task satisfies
  the five-part exception in
  `docs/project-control/10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md`;
- `run_mps_hypothesis_screen.py` and `run_mps_limitation_screen.py` record
  consumed one-shot research lanes and must not be rerun by inference;
- provider/API/network, Vault, report mutation, runtime, paper, live, broker, and
  state-changing commands require exact task authority;
- output must never overwrite immutable decision evidence;
- credentials and token contents must never be logged or committed.

Before using any script, read the current project-control files, name the exact
script and inputs, define output and resource bounds, state whether network/API
access is allowed, and define a stop condition.
