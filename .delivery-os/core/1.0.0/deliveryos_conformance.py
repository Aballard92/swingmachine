#!/usr/bin/env python3
"""DeliveryOS standard-library-only contract conformance CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SHARED_RULES = {
    "issue_as_contract",
    "exact_release_pin",
    "exact_commit_pin",
    "sponsor_acceptance",
    "no_silent_upgrades",
    "no_automatic_cross_repo_mutation",
}
PINNED_CORE_FILES = (
    "GOVERNANCE.md",
    "VERSION",
    "deliveryos_conformance.py",
    "docs/01-north-star-and-mvp.md",
    "docs/02-roles-and-authority.md",
    "docs/03-feature-and-backlog-model.md",
    "docs/04-issue-as-contract.md",
    "docs/05-goal-and-handover.md",
    "docs/06-review-and-change-control.md",
    "docs/07-risk-permissions-and-evidence.md",
    "docs/08-adoption-and-versioning.md",
    "pinned-core-files.json",
    "schemas/feature-contract.schema.json",
    "schemas/project-manifest.schema.json",
    "templates/goal.md",
    "templates/merge.md",
    "templates/project-overlay.yml",
    "templates/review.md",
)
SNAPSHOT_LOCK = "snapshot-lock.json"
STABLE_VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
FULL_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class ConformanceError(ValueError):
    """A contract cannot be parsed or does not conform."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(document: Any) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _relative_files(root: Path) -> set[str]:
    files = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ConformanceError(f"snapshot integrity: symlink is prohibited: {path.relative_to(root).as_posix()}")
        if path.is_file():
            files.add(path.relative_to(root).as_posix())
    return files


def _require_builtin_allowlist() -> None:
    if tuple(sorted(PINNED_CORE_FILES)) != PINNED_CORE_FILES or len(set(PINNED_CORE_FILES)) != len(PINNED_CORE_FILES):
        raise ConformanceError("snapshot integrity: built-in pinned-core allowlist is not sorted and unique")
    for relative in PINNED_CORE_FILES:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != relative:
            raise ConformanceError("snapshot integrity: built-in pinned-core allowlist contains an unsafe path")


def _require_snapshot_allowlist(source_root: Path) -> None:
    _require_builtin_allowlist()
    allowlist_path = source_root / "pinned-core-files.json"
    try:
        document = json.loads(allowlist_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConformanceError("snapshot integrity: pinned-core allowlist is unreadable") from exc
    if document != list(PINNED_CORE_FILES):
        raise ConformanceError("snapshot integrity: pinned-core allowlist differs from the deterministic CLI allowlist")
    for relative in PINNED_CORE_FILES:
        candidate = source_root / relative
        if candidate.is_symlink() or not candidate.is_file():
            raise ConformanceError(f"snapshot integrity: required source file missing or not regular: {relative}")


def _git(source_root: Path, *args: str) -> bytes:
    """Run Git without a shell and return stdout bytes or a stable safe error."""
    try:
        process = subprocess.run(
            ["git", "-C", str(source_root), *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise ConformanceError("snapshot creation: Git is unavailable") from exc
    if process.returncode != 0:
        raise ConformanceError(f"snapshot creation: Git command failed: {args[0]}")
    return process.stdout


def _commit_blobs(source_root: Path, commit: str, version: str) -> dict[str, bytes]:
    """Resolve one exact commit and load every allowlisted regular blob from it."""
    _require_builtin_allowlist()
    try:
        repository_root = Path(_git(source_root, "rev-parse", "--show-toplevel").decode("utf-8").strip()).resolve()
    except (UnicodeDecodeError, ValueError) as exc:
        raise ConformanceError("snapshot creation: Git repository root is invalid") from exc
    if repository_root != source_root:
        raise ConformanceError("snapshot creation: source root must be the Git repository root")
    try:
        resolved = _git(source_root, "rev-parse", "--verify", f"{commit}^{{commit}}").decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise ConformanceError("snapshot creation: resolved commit is invalid") from exc
    if resolved != commit:
        raise ConformanceError("snapshot creation: resolved commit does not exactly equal the supplied full SHA")

    blobs: dict[str, bytes] = {}
    for relative in PINNED_CORE_FILES:
        record = _git(source_root, "ls-tree", "-z", commit, "--", relative)
        entries = [entry for entry in record.split(b"\0") if entry]
        if len(entries) != 1 or b"\t" not in entries[0]:
            raise ConformanceError(f"snapshot creation: allowlisted path is missing at commit: {relative}")
        metadata, raw_path = entries[0].split(b"\t", 1)
        fields = metadata.split()
        try:
            committed_path = raw_path.decode("utf-8")
            mode, object_type, object_id = (field.decode("ascii") for field in fields)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ConformanceError(f"snapshot creation: invalid Git tree entry: {relative}") from exc
        if committed_path != relative:
            raise ConformanceError(f"snapshot creation: Git tree path mismatch: {relative}")
        if mode not in {"100644", "100755"} or object_type != "blob" or not re.fullmatch(r"[0-9a-f]{40,64}", object_id):
            raise ConformanceError(f"snapshot creation: allowlisted path is not a regular blob: {relative}")
        blobs[relative] = _git(source_root, "cat-file", "blob", object_id)

    try:
        committed_version = blobs["VERSION"].decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise ConformanceError("snapshot creation: committed VERSION is not UTF-8") from exc
    if committed_version != version:
        raise ConformanceError("snapshot creation: VERSION at commit does not equal the requested version")
    try:
        committed_allowlist = json.loads(blobs["pinned-core-files.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConformanceError("snapshot creation: committed pinned-core allowlist is invalid") from exc
    if committed_allowlist != list(PINNED_CORE_FILES):
        raise ConformanceError("snapshot creation: committed pinned-core allowlist differs from the built-in sorted allowlist")
    return blobs


def create_snapshot(source_root: Path, snapshot_root: Path, version: str, commit: str) -> dict[str, Any]:
    """Create an immutable deterministic core copy and lock metadata."""
    source_root = source_root.resolve()
    snapshot_root = snapshot_root.resolve()
    if not STABLE_VERSION.fullmatch(version):
        raise ConformanceError("snapshot creation: version must be an accepted stable semantic version")
    if not FULL_COMMIT.fullmatch(commit):
        raise ConformanceError("snapshot creation: commit must be a full 40-character lowercase SHA")
    blobs = _commit_blobs(source_root, commit, version)
    if snapshot_root.exists():
        raise ConformanceError("snapshot creation: destination already exists; snapshots are never overwritten")
    try:
        snapshot_root.mkdir(parents=True)
        for relative in PINNED_CORE_FILES:
            destination = snapshot_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(blobs[relative])
        lock = {
            "schema_version": 1,
            "delivery_os": {"commit": commit, "version": version},
            "files": [
                {"path": relative, "sha256": _sha256(snapshot_root / relative)}
                for relative in PINNED_CORE_FILES
            ],
        }
        (snapshot_root / SNAPSHOT_LOCK).write_bytes(_canonical_json(lock))
    except Exception:
        shutil.rmtree(snapshot_root, ignore_errors=True)
        raise
    return {
        "commit": commit,
        "snapshot_lock_sha256": _sha256(snapshot_root / SNAPSHOT_LOCK),
        "version": version,
    }


def _strip_comment(line: str) -> str:
    quote = None
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote == '"':
            escaped = True
            continue
        if char in {"'", '"'}:
            quote = None if quote == char else char if quote is None else quote
        elif char == "#" and quote is None and (index == 0 or line[index - 1].isspace()):
            return line[:index].rstrip()
    return line.rstrip()


def _split_flow(value: str) -> list[str]:
    parts, current = [], []
    depth = 0
    quote = None
    for char in value:
        if char in {"'", '"'}:
            quote = None if quote == char else char if quote is None else quote
        elif quote is None and char in "[{":
            depth += 1
        elif quote is None and char in "]}":
            depth -= 1
        if char == "," and quote is None and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if current or value.strip():
        parts.append("".join(current).strip())
    return parts


def _split_key_value(value: str, line_number: int) -> tuple[str, str]:
    quote = None
    depth = 0
    for index, char in enumerate(value):
        if char in {"'", '"'}:
            quote = None if quote == char else char if quote is None else quote
        elif quote is None and char in "[{":
            depth += 1
        elif quote is None and char in "]}":
            depth -= 1
        elif char == ":" and quote is None and depth == 0:
            key = value[:index].strip()
            if not key:
                break
            return key, value[index + 1 :].strip()
    raise ConformanceError(f"YAML line {line_number}: expected key: value")


def _scalar(value: str, line_number: int) -> Any:
    value = value.strip()
    if value == "":
        return None
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if re.fullmatch(r"-?(0|[1-9][0-9]*)", value):
        return int(value)
    if value.startswith('"') and value.endswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise ConformanceError(f"YAML line {line_number}: invalid quoted string") from exc
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    if value.startswith("[") and value.endswith("]"):
        inside = value[1:-1].strip()
        return [] if not inside else [_scalar(part, line_number) for part in _split_flow(inside)]
    if value.startswith("{") and value.endswith("}"):
        result = {}
        inside = value[1:-1].strip()
        for part in ([] if not inside else _split_flow(inside)):
            key, item = _split_key_value(part, line_number)
            if key in result:
                raise ConformanceError(f"YAML line {line_number}: duplicate key {key}")
            result[key] = _scalar(item, line_number)
        return result
    if value[0] in "[{" or value[-1] in "]}":
        raise ConformanceError(f"YAML line {line_number}: malformed flow collection")
    if any(token in value for token in ("&", "*", "!", "|", ">")):
        raise ConformanceError(f"YAML line {line_number}: unsupported YAML feature")
    return value


def parse_yaml(text: str) -> Any:
    """Parse the documented deterministic YAML subset."""
    lines: list[tuple[int, str, int]] = []
    for number, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw:
            raise ConformanceError(f"YAML line {number}: tabs are not allowed")
        cleaned = _strip_comment(raw)
        if not cleaned.strip() or cleaned.lstrip().startswith("---"):
            continue
        indent = len(cleaned) - len(cleaned.lstrip(" "))
        if indent % 2:
            raise ConformanceError(f"YAML line {number}: indentation must use two spaces")
        lines.append((indent, cleaned.strip(), number))
    if not lines:
        return {}

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(lines) or lines[index][0] < indent:
            return {}, index
        is_list = lines[index][1] == "-" or lines[index][1].startswith("- ")
        container: Any = [] if is_list else {}
        while index < len(lines):
            current_indent, content, number = lines[index]
            if current_indent < indent:
                break
            if current_indent > indent:
                raise ConformanceError(f"YAML line {number}: unexpected indentation")
            if is_list:
                if not (content == "-" or content.startswith("- ")):
                    break
                item_text = content[1:].strip()
                index += 1
                if not item_text:
                    if index >= len(lines) or lines[index][0] <= indent:
                        raise ConformanceError(f"YAML line {number}: empty list item")
                    item, index = parse_block(index, indent + 2)
                elif ":" in item_text:
                    key, raw_value = _split_key_value(item_text, number)
                    item = {key: _scalar(raw_value, number)}
                    if raw_value == "":
                        if index >= len(lines) or lines[index][0] <= indent:
                            raise ConformanceError(f"YAML line {number}: missing nested value")
                        item[key], index = parse_block(index, indent + 2)
                    if index < len(lines) and lines[index][0] == indent + 2:
                        extra, index = parse_block(index, indent + 2)
                        if not isinstance(extra, dict):
                            raise ConformanceError(f"YAML line {number}: list mapping expected")
                        overlap = set(item).intersection(extra)
                        if overlap:
                            raise ConformanceError(f"YAML line {number}: duplicate key {sorted(overlap)[0]}")
                        item.update(extra)
                else:
                    item = _scalar(item_text, number)
                container.append(item)
            else:
                if content == "-" or content.startswith("- "):
                    break
                key, raw_value = _split_key_value(content, number)
                if key in container:
                    raise ConformanceError(f"YAML line {number}: duplicate key {key}")
                index += 1
                if raw_value == "":
                    if index >= len(lines) or lines[index][0] <= indent:
                        value = None
                    else:
                        value, index = parse_block(index, indent + 2)
                else:
                    value = _scalar(raw_value, number)
                container[key] = value
        return container, index

    parsed, final = parse_block(0, lines[0][0])
    if final != len(lines):
        raise ConformanceError(f"YAML line {lines[final][2]}: could not parse document")
    return parsed


def load_document(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    try:
        if path.suffix == ".json":
            return json.loads(text)
        if path.suffix in {".yml", ".yaml"}:
            if text.lstrip().startswith(("{", "[")):
                return json.loads(text)
            return parse_yaml(text)
    except (json.JSONDecodeError, ConformanceError) as exc:
        raise ConformanceError(f"{path}: parse error: {exc}") from exc
    raise ConformanceError(f"{path}: unsupported file type")


def _type_matches(value: Any, expected: str) -> bool:
    types = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "boolean": bool,
        "null": type(None),
    }
    if expected == "integer" and isinstance(value, bool):
        return False
    return isinstance(value, types[expected])


def validate_schema(instance: Any, schema: dict[str, Any], location: str = "$") -> list[str]:
    """Validate the JSON Schema keywords used by the bundled schemas."""
    errors: list[str] = []
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{location}: must equal {schema['const']!r}")
    expected = schema.get("type")
    if expected and not _type_matches(instance, expected):
        return errors + [f"{location}: expected {expected}"]
    if isinstance(instance, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                errors.append(f"{location}: missing required property {key}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in instance.keys() - properties.keys():
                errors.append(f"{location}: unexpected property {key}")
        for key, value in instance.items():
            if key in properties:
                errors.extend(validate_schema(value, properties[key], f"{location}.{key}"))
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{location}: needs at least {schema['minItems']} item(s)")
        if "items" in schema:
            for index, value in enumerate(instance):
                errors.extend(validate_schema(value, schema["items"], f"{location}[{index}]"))
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{location}: string is too short")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], instance):
            errors.append(f"{location}: does not match required pattern")
        if "enum" in schema and instance not in schema["enum"]:
            errors.append(f"{location}: value is not allowed")
    return errors


def validate_project_manifest(document: Any) -> list[str]:
    schema = load_document(ROOT / "schemas/project-manifest.schema.json")
    errors = validate_schema(document, schema)
    if errors:
        return [f"project manifest: {error}" for error in errors]
    version = document["delivery_os"]["version"]
    release_url = document["delivery_os"]["release_url"]
    snapshot = document["delivery_os"]["snapshot"]
    if not release_url.endswith(f"/v{version}"):
        errors.append("project manifest: release URL must match the exact version")
    if version not in snapshot.split("/"):
        errors.append("project manifest: snapshot path must include the exact version")
    return errors


def validate_feature_contract(document: Any) -> list[str]:
    schema = load_document(ROOT / "schemas/feature-contract.schema.json")
    return [f"feature contract: {error}" for error in validate_schema(document, schema)]


def validate_overlay(document: Any) -> list[str]:
    errors = []
    if not isinstance(document, dict):
        return ["project overlay: expected object"]
    for section in ("schema_version", "project", "delivery", "shared_rules"):
        if section not in document:
            errors.append(f"project overlay: missing {section}")
    rules = document.get("shared_rules", {})
    if not isinstance(rules, dict):
        return errors + ["project overlay: shared_rules must be an object"]
    for rule in sorted(SHARED_RULES):
        if rules.get(rule) != "required":
            errors.append(f"shared rule {rule} must remain required")
    unknown = set(rules) - SHARED_RULES
    if unknown:
        errors.append(f"project overlay: unknown shared rules: {', '.join(sorted(unknown))}")
    stricter = document.get("delivery", {}).get("stricter_rules") if isinstance(document.get("delivery"), dict) else None
    if not isinstance(stricter, list):
        errors.append("project overlay: delivery.stricter_rules must be a list")
    return errors


def validate_adoption(
    manifest_path: Path,
    overlay_path: Path,
    snapshot_root: Path,
    cli_path: Path,
) -> list[str]:
    """Validate a manifest, overlay, locked snapshot, and pinned CLI as one unit."""
    errors: list[str] = []
    manifest = load_document(manifest_path)
    overlay = load_document(overlay_path)
    manifest_errors = validate_project_manifest(manifest)
    overlay_errors = validate_overlay(overlay)
    errors.extend(manifest_errors)
    errors.extend(overlay_errors)
    if manifest_errors or overlay_errors:
        return errors

    manifest_path = manifest_path.resolve()
    overlay_path = overlay_path.resolve()
    snapshot_root = snapshot_root.resolve()
    cli_path = cli_path.resolve()
    project_root = manifest_path.parent

    if manifest["project"]["id"] != overlay.get("project", {}).get("id"):
        errors.append("adoption integrity: project ID mismatch between manifest and overlay")
    expected_overlay = (project_root / manifest["overlay"]).resolve()
    if overlay_path != expected_overlay:
        errors.append("adoption integrity: supplied overlay path does not equal manifest.overlay")
    expected_snapshot = (project_root / manifest["delivery_os"]["snapshot"]).resolve()
    if snapshot_root != expected_snapshot:
        errors.append("adoption integrity: supplied snapshot root does not equal manifest.delivery_os.snapshot")
    expected_cli = (snapshot_root / "deliveryos_conformance.py").resolve()
    try:
        cli_path.relative_to(snapshot_root)
    except ValueError:
        errors.append("adoption integrity: CLI is outside the snapshot")
    if cli_path != expected_cli:
        errors.append("adoption integrity: CLI must be the required pinned CLI inside the snapshot")

    lock_path = snapshot_root / SNAPSHOT_LOCK
    try:
        lock_bytes = lock_path.read_bytes()
        lock = json.loads(lock_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        return errors + [f"snapshot integrity: lock metadata is missing or unreadable: {exc.__class__.__name__}"]

    expected_lock_hash = manifest["delivery_os"]["snapshot_lock_sha256"]
    actual_lock_hash = hashlib.sha256(lock_bytes).hexdigest()
    if actual_lock_hash != expected_lock_hash:
        errors.append("snapshot integrity: snapshot lock digest does not match manifest")
    if not isinstance(lock, dict) or set(lock) != {"schema_version", "delivery_os", "files"}:
        return errors + ["snapshot integrity: lock metadata shape is invalid"]
    if lock.get("schema_version") != 1:
        errors.append("snapshot integrity: lock schema version must equal 1")
    metadata = lock.get("delivery_os")
    if not isinstance(metadata, dict) or set(metadata) != {"commit", "version"}:
        return errors + ["snapshot integrity: delivery_os lock metadata shape is invalid"]
    if metadata.get("version") != manifest["delivery_os"]["version"]:
        errors.append("snapshot integrity: snapshot version mismatch")
    if metadata.get("commit") != manifest["delivery_os"]["commit"]:
        errors.append("snapshot integrity: snapshot commit mismatch")

    try:
        _require_snapshot_allowlist(snapshot_root)
    except ConformanceError as exc:
        errors.append(str(exc))
    try:
        actual_files = _relative_files(snapshot_root) if snapshot_root.is_dir() else set()
    except ConformanceError as exc:
        errors.append(str(exc))
        actual_files = set()
    expected_files = set(PINNED_CORE_FILES) | {SNAPSHOT_LOCK}
    for missing in sorted(expected_files - actual_files):
        errors.append(f"snapshot integrity: required snapshot file missing: {missing}")
    for extra in sorted(actual_files - expected_files):
        errors.append(f"snapshot integrity: unexpected snapshot file: {extra}")

    file_records = lock.get("files")
    if not isinstance(file_records, list):
        return errors + ["snapshot integrity: lock files must be a list"]
    locked_paths = []
    locked_hashes: dict[str, str] = {}
    for record in file_records:
        if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
            errors.append("snapshot integrity: file record shape is invalid")
            continue
        path = record.get("path")
        digest = record.get("sha256")
        if not isinstance(path, str) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append("snapshot integrity: file record values are invalid")
            continue
        locked_paths.append(path)
        locked_hashes[path] = digest
    if locked_paths != list(PINNED_CORE_FILES):
        errors.append("snapshot integrity: locked file allowlist is missing, reordered, duplicated, or changed")
    for relative in PINNED_CORE_FILES:
        path = snapshot_root / relative
        if path.is_file() and locked_hashes.get(relative) != _sha256(path):
            errors.append(f"snapshot integrity: snapshot file altered: {relative}")
    version_path = snapshot_root / "VERSION"
    if version_path.is_file() and version_path.read_text(encoding="utf-8").strip() != manifest["delivery_os"]["version"]:
        errors.append("snapshot integrity: VERSION file does not equal manifest version")
    return errors


def validate_path(path: Path) -> list[str]:
    document = load_document(path)
    name = path.name
    if "project-manifest" in name or name in {".delivery-os.yml", ".delivery-os.yaml"}:
        return validate_project_manifest(document)
    if "feature-contract" in name:
        return validate_feature_contract(document)
    if "overlay" in name:
        return validate_overlay(document)
    raise ConformanceError(f"{path}: cannot infer contract type")


def check_examples(root: Path = ROOT) -> tuple[int, int, list[str]]:
    expectations = load_document(root / "examples/expectations.json")
    passed = rejected = 0
    failures = []
    for relative, expectation in expectations.items():
        path = root / "examples" / relative
        try:
            errors = validate_path(path)
        except ConformanceError as exc:
            errors = [str(exc)]
        if expectation == "pass":
            if errors:
                failures.append(f"{relative}: expected pass, got {'; '.join(errors)}")
            else:
                passed += 1
        else:
            combined = "; ".join(errors)
            if not errors:
                failures.append(f"{relative}: expected rejection containing {expectation!r}, got pass")
            elif expectation not in combined:
                failures.append(f"{relative}: rejection did not contain {expectation!r}: {combined}")
            else:
                rejected += 1
    return passed, rejected, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="validate a manifest, feature contract, or overlay")
    validate.add_argument("paths", nargs="+", type=Path)
    yaml_parser = sub.add_parser("parse-yaml", help="parse YAML-subset documents")
    yaml_parser.add_argument("paths", nargs="+", type=Path)
    snapshot = sub.add_parser("create-snapshot", help="create a deterministic locked pinned-core snapshot")
    snapshot.add_argument("--source-root", required=True, type=Path)
    snapshot.add_argument("--snapshot-root", required=True, type=Path)
    snapshot.add_argument("--version", required=True)
    snapshot.add_argument("--commit", required=True)
    adoption = sub.add_parser("validate-adoption", help="validate a complete pinned adoption as one unit")
    adoption.add_argument("--manifest", required=True, type=Path)
    adoption.add_argument("--overlay", required=True, type=Path)
    adoption.add_argument("--snapshot-root", required=True, type=Path)
    adoption.add_argument("--cli", required=True, type=Path)
    sub.add_parser("check-examples", help="run the valid/invalid example matrix")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            failures = []
            for path in args.paths:
                failures.extend(f"{path}: {error}" for error in validate_path(path))
            if failures:
                print("\n".join(failures), file=sys.stderr)
                return 1
            print(f"PASS: {len(args.paths)} contract(s)")
        elif args.command == "parse-yaml":
            for path in args.paths:
                load_document(path)
            print(f"PASS: {len(args.paths)} YAML document(s)")
        elif args.command == "create-snapshot":
            result = create_snapshot(args.source_root, args.snapshot_root, args.version, args.commit)
            print(json.dumps(result, sort_keys=True))
        elif args.command == "validate-adoption":
            failures = validate_adoption(args.manifest, args.overlay, args.snapshot_root, args.cli)
            if failures:
                print("\n".join(failures), file=sys.stderr)
                return 1
            print("PASS: coherent pinned adoption")
        else:
            passed, rejected, failures = check_examples()
            if failures:
                print("\n".join(failures), file=sys.stderr)
                return 1
            print(f"PASS: {passed} valid example(s); REJECTED: {rejected} invalid example(s)")
    except (OSError, ConformanceError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
