# Roles and Authority

## Sponsor

The Sponsor owns final acceptance, rejection, prioritisation, permission expansion, product decisions, release approval, and adoption approval. Sponsor acceptance must be explicit and recorded.

## Project owner

The adopting repository owns product direction and local rules. This authority cannot be transferred to DeliveryOS by a manifest, snapshot, overlay, template, or automation result.

## Delivery agent

A delivery agent may analyse, edit, test, and publish only within the current issue's permissions. It must preserve unrelated work, stop at stated gates, report evidence accurately, and never infer authority from access.

## Reviewer

A reviewer independently checks the frozen contract, diff, evidence, tests, ownership boundary, and permissions. A reviewer does not rewrite acceptance after implementation or substitute for the Sponsor.

## Automation

Automation parses and validates contracts. It cannot approve scope, waive a rule, accept a release, or make a product decision.

## Conflict order

Within shared mechanics: accepted pinned core, then additive overlay, then feature issue. The feature issue may narrow permissions further. Product and domain rules always remain local; where a local rule is stricter, it prevails. Any unclear conflict is a stop condition requiring a decision issue.
