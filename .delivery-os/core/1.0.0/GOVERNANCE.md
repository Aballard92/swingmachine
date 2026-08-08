# Governance

## Authority

The Sponsor is the human final decision-maker. The Sponsor accepts, rejects, revises, rolls back, or defers DeliveryOS releases and project adoptions. Reviewers provide independent findings. Delivery agents implement only an authorised issue contract. Automation validates evidence but has no acceptance authority.

## Change contract

Every shared-core change requires:

1. an issue stating outcome, scope, trust model, permissions, frozen acceptance, independent tests, and stop conditions;
2. a branch and pull request;
3. passing conformance and review evidence;
4. explicit Sponsor acceptance; and
5. a versioned release from an accepted merged commit.

No issue, PR, test, review, or generated artifact by itself constitutes Sponsor acceptance. Acceptance must be recorded explicitly.

## Release policy

- Release candidates use a semantic-version prerelease suffix and are never adoptable.
- An accepted release uses an immutable semantic version and resolves to one full 40-character commit SHA.
- A version is never retargeted. Corrections require a new version.
- Releases are created only from accepted commits on `main` under separately authorised work.
- No silent upgrades, floating refs, automatic cross-repo mutation, or implied adoption.

## Compatibility and overlays

Shared required rules are minimums. A project overlay may add evidence, narrower permissions, stronger approvals, or stricter tests. It may not disable requirements, broaden permissions granted by the feature issue, replace local domain rules, or conceal a conflict. Conflicts stop adoption and require an explicit decision issue.

## Ownership

DeliveryOS owns only shared delivery mechanics. Each project owns its product North Star, MVP, architecture, state, decisions, risks, backlog, code, feature issues, domain policy, data, runtime, and releases. DeliveryOS does not create a combined product backlog.

## Security and services

The core uses the Python standard library and GitHub-hosted repository features. Paid services and unnecessary frameworks are outside v1. Secrets, account access, provider calls, runtime mutation, and product data are never implied by a DeliveryOS contract.
