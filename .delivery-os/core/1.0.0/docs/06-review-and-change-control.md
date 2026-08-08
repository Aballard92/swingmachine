# Review and Change Control

## Independent review

Review the exact issue, base/head refs, full diff, permission boundary, acceptance criteria, tests, evidence, and unresolved defects. Confirm shared/local ownership and check that automation claims do not exceed evidence.

## Change path

All shared changes require issue, PR, independent review, Sponsor acceptance, merge, and a new immutable versioned release. Adoption changes require their own local issue and PR after the release gate. There are no silent upgrades or automatic cross-repo mutations.

## Review outcomes

- **Accept:** frozen acceptance and permissions are satisfied; Sponsor may approve merge/release separately.
- **Revise:** required work remains within scope.
- **Block:** a stop condition, guardrail conflict, unverifiable claim, or permission breach exists.
- **Follow-up:** non-blocking hardening has a linked owner and issue.

## Merge controls

Passing CI is necessary where required but not sufficient. Merge requires explicit Sponsor acceptance, resolved blocking defects, exact evidence, and correct target branch. Release/tag creation is a separate authorised action. Draft PRs and release candidates must not be adopted.
