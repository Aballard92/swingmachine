# Adoption and Versioning

## Gate sequence

1. Foundation candidate is reviewed in a draft PR.
2. Sponsor explicitly accepts the candidate.
3. The accepted commit merges to `main`.
4. A separately authorised immutable semantic version/release is created for that full commit SHA.
5. A pilot's adoption issue receives explicit implementation permission.
6. The pilot pins the exact accepted version and full commit, generates the core snapshot, adds its overlay, runs conformance, and opens its own PR.

No pilot may pin a release candidate, unaccepted version, branch, mutable `main`, short SHA, or moving tag.

## Integration files

- `.delivery-os.yml`: project ID, accepted version, exact full commit, release/source URLs, snapshot path, snapshot-lock SHA-256, overlay path, and acceptance flag.
- Generated snapshot: reproducible shared-core files from the pinned commit; never hand-edited.
- Local overlay: sources of truth and additive/stricter mechanics.
- Targeted local agent reference: points to the integration without replacing domain rules.

## Overlay rule

The shared minimums are issue-as-contract, exact release pin, exact commit pin, Sponsor acceptance, no silent upgrade, and no automatic cross-repo mutation. An overlay may add sources, approvals, evidence, tests, stop conditions, or prohibitions. It cannot set a minimum to optional/disabled, delete it, broaden feature permissions, or supersede local product policy.

## YAML subset

The v1 standard-library parser accepts UTF-8 YAML containing indentation-based mappings and lists, simple flow mappings/lists, plain or quoted scalar strings, booleans, null, integers, and comments. Tabs, anchors, aliases, tags, multiline scalars, floats, duplicate keys, and implicit dates are rejected. JSON remains valid YAML input.

## Upgrade

Every upgrade is an explicit local issue/PR that changes both version and commit, regenerates the snapshot, reviews release notes, reconciles the overlay, and reruns conformance. DeliveryOS never pushes into a pilot automatically.

## Generate and lock a snapshot

Only after the release gate, use a local DeliveryOS Git repository whose object database already contains the exact accepted commit. `--source-root` must resolve to that repository's top level. Snapshot creation does not fetch or use the network.

The supplied full lowercase SHA is resolved as a commit object and must resolve exactly to itself. For every allowlisted path, the command reads the tree entry and blob from that commit through safe argument-list Git subprocesses. Only regular `100644` or `100755` blobs are accepted; missing paths, symlinks, submodules/gitlinks, trees, and other entry types are rejected. `VERSION` and `pinned-core-files.json` are parsed from those committed blob bytes, not from the checkout.

The current branch, checked-out commit, newer `HEAD`, dirty tracked files, and untracked files cannot influence output. A clean checkout is still good operational hygiene, but it is not part of the trust mechanism. The command also refuses prerelease versions, abbreviated/nonexistent commits, a committed `VERSION` mismatch, an invalid committed allowlist, and an existing destination. It never discovers or edits pilot repositories automatically.

```bash
python3 /verified/DeliveryOS/deliveryos_conformance.py create-snapshot \
  --source-root /verified/DeliveryOS \
  --snapshot-root "$PWD/.delivery-os/core/1.0.0" \
  --version 1.0.0 \
  --commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

The explicit sorted allowlist is [`pinned-core-files.json`](../pinned-core-files.json). Creation copies only those files and writes `snapshot-lock.json` with schema version, accepted DeliveryOS version, full commit, ordered relative paths, and SHA-256 hashes. Canonical JSON contains no timestamp, source path, username, hostname, or other machine-specific value. The command prints the lock SHA-256; record it as `delivery_os.snapshot_lock_sha256` in `.delivery-os.yml`.

Creating the same version/commit from the same Git object in two empty destinations produces byte-identical snapshots, regardless of working-tree state. A destination is never overwritten. An upgrade first ensures the new accepted commit object is present locally, then uses a new versioned directory, updates both manifest version/commit and lock digest, reconciles the overlay, and passes review before the older snapshot is removed under separate local authority.

## Verify the complete adoption

Run the CLI from inside the generated snapshot and supply every relational path explicitly:

```bash
python3 .delivery-os/core/1.0.0/deliveryos_conformance.py validate-adoption \
  --manifest .delivery-os.yml \
  --overlay .delivery-os/overlay.yml \
  --snapshot-root .delivery-os/core/1.0.0 \
  --cli .delivery-os/core/1.0.0/deliveryos_conformance.py
```

Validation fails closed unless manifest and overlay project IDs match; supplied paths equal the manifest; the manifest is accepted and exactly versioned; lock version/commit equal the manifest; lock digest equals the manifest; the pinned CLI is at its required in-snapshot path; the allowlist is exact; every required file is present, regular, unchanged, and correctly hashed; and there are no extra files. Independent manifest/overlay validation is not an adoption acceptance check.

## Reusable workflow access and pinned local fallback

The reusable workflow must be referenced by the exact accepted full commit, never `main`. Because DeliveryOS is private, GitHub requires its **Settings > Actions > General > Access** policy to allow private repositories owned by `Aballard92`, and each caller must allow the reusable workflow. GitHub documents this prerequisite in [Sharing actions and workflows from your private repository](https://docs.github.com/en/actions/how-tos/reuse-automations/share-across-private-repositories). At R1 review time the DeliveryOS API reported `access_level: none`; R1 does not change that setting.

Until access is separately authorised and verified, use the deterministic pinned local command above in pilot CI. It executes the CLI already inside the reviewed generated snapshot and therefore does not fetch or drift to mutable DeliveryOS state. Whether hosted reuse or the local fallback is used, the same four inputs—manifest, overlay, snapshot root, and in-snapshot CLI—must be passed to `validate-adoption`.

## Rollback

Rollback pins a previously accepted immutable version/commit through the same local change controls. Never edit or retarget an existing release.
