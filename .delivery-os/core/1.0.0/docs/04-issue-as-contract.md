# Issue as Contract

The authoritative issue is the durable contract for bounded work. Templates help create it; chat, `/goal`, branches, commits, and PRs point back to it and cannot silently widen it.

## Required contract sections

The feature form uses the following distinct required vocabulary. The JSON schema represents `scope` and `non_scope` as `scope.included` and `scope.excluded`; all other contract fields are required top-level schema properties.

<!-- feature-contract-vocabulary:start -->
- `outcome`: outcome and value;
- `why_now`: why the feature is needed now;
- `accepted_state`: independently observable completion;
- `scope`: included work;
- `non_scope`: explicitly excluded work;
- `architecture_and_ownership`: architecture and ownership boundaries;
- `trust_model`: authorities, assumptions, provenance, and evidence limits;
- `permissions`: allowed and prohibited actions;
- `deliverables`: concrete outputs;
- `acceptance_criteria`: frozen acceptance criteria;
- `independent_tests`: tests independent of implementation claims;
- `evidence_required`: exact evidence and reporting;
- `defect_policy`: blocking defects versus follow-up hardening;
- `stop_conditions`: fail-closed and escalation conditions;
- `change_control`: amendment authority and process;
- `pr_merge_policy`: branch, PR, review, merge, and release policy;
- `handover`: compact completion or blocker format.
<!-- feature-contract-vocabulary:end -->

## Freeze and amendment

Acceptance is frozen when implementation begins. A material amendment is an explicit issue edit or linked decision with reason, impact, and Sponsor approval. The PR must identify the amendment. Hidden scope expansion, test deletion, permission broadening, or post-hoc acceptance rewriting is non-conformant.

## Feature integrity

Deliver the coherent feature. Fixes required for its accepted behaviour stay inside it. Split only independently valuable follow-up hardening that does not undermine current acceptance.
