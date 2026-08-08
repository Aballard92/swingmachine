# Feature and Backlog Model

## Local backlog ownership

Every repository owns its own backlog. DeliveryOS supplies mechanics and templates, not priorities or product items. Cross-repo visibility must never become a combined product backlog.

## Feature as delivery unit

A feature is a coherent outcome with one authoritative feature issue. The issue freezes:

- value and scope;
- trust assumptions and evidence limits;
- allowed and prohibited permissions;
- acceptance criteria;
- independent tests;
- blocking-defect and follow-up-hardening policy.

Implementation, documentation, tests, and acceptance evidence should travel together when they serve that feature. A required fix remains in the feature rather than being detached to make incomplete work appear complete.

## Discovery and decisions

Discovery issues reduce uncertainty without granting implementation. Decision issues record an explicit choice, owner, alternatives, consequences, and expiry/revisit trigger. Their conclusions update a feature contract only through a visible issue change accepted by the Sponsor.

## Defects

A blocking defect prevents a frozen acceptance criterion, violates permissions or trust assumptions, risks data/state/security, or makes evidence unreliable. It must be fixed before acceptance within the feature or explicitly remove acceptance through Sponsor-approved change control.

Follow-up hardening improves resilience, clarity, operability, or coverage without invalidating frozen acceptance. It receives a linked local backlog issue and must not disguise a blocking defect.
