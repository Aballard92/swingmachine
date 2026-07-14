# Compact `/goal` and Handover

## `/goal`

`/goal` is a pointer, not a second contract. Use:

```text
/goal <repo> <issue-url-or-number>
```

The agent reads the full issue and current repository authority before acting. If chat and issue differ materially, stop and ask the Sponsor to amend or clarify the durable contract. Never use `/goal` to infer missing permissions.

## Working updates

Updates state the current checkpoint, evidence obtained, failures, and stop conditions without claiming acceptance.

## Handover

A compact handover contains task ID, state, authoritative issue, PR when present, and a short blocker when blocked:

```text
<TASK-ID> READY <repo> #<issue> PR #<pr>
<TASK-ID> BLOCKED - <short evidence-based reason>
```

`READY` means ready for independent review under the frozen contract, not merged, released, deployed, adopted, or Sponsor-accepted. Detailed evidence belongs on the issue and PR.
