from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from . import __version__


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _manifest(package: Path) -> tuple[dict, Path]:
    manifest_path = package / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"not a Lore package: missing {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8")), manifest_path


def inspect_package(path: Path) -> int:
    manifest, _ = _manifest(path)
    print(json.dumps(manifest, indent=2))
    return 0


# Roughly the character budget of a 512-token embedding window. Text beyond it
# is not represented by the record's vector, so retrieval is blind to it. This
# is a heuristic for reporting, never for rejection — a package with long
# records is importable, its retrieval simply cannot be trusted to reach past
# the opening of each record.
_EMBEDDING_WINDOW_CHARS = 2000


def _declared_digests(package: Path, manifest: dict) -> tuple[dict[str, str], str]:
    """Return the digests to verify against, and where they came from.

    PACKAGE_FORMAT.md requires SHA-256 hashes for every artifact in the manifest
    itself. That placement matters: the manifest is what the signature covers,
    so digests carried there are transitively signed. Digests carried only in a
    separate checksums.json are not — an edit to a payload file and its checksum
    entry leaves any signature over the manifest still valid.

    Both sources are accepted so packages built before this requirement was
    enforced remain verifiable, but the source is reported so an operator can
    see whether the digests were covered by a signature or merely alongside one.
    """
    inline = manifest.get("artifact_digests")
    if isinstance(inline, dict) and inline:
        return {str(k): str(v) for k, v in inline.items()}, "manifest"

    checksums_name = manifest.get("artifacts", {}).get("checksums", "checksums.json")
    checksums_path = package / checksums_name
    if not checksums_path.is_file():
        return {}, "none"
    loaded = json.loads(checksums_path.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in loaded.items()}, checksums_name


def _verify_digests(package: Path, digests: dict[str, str]) -> list[dict[str, str]]:
    """Recompute every declared digest. Returns one entry per failure."""
    failures: list[dict[str, str]] = []
    for name, expected in sorted(digests.items()):
        target = package / name
        if not target.is_file():
            failures.append({"artifact": name, "reason": "missing"})
            continue
        actual = _sha256(target)
        if actual != expected:
            failures.append(
                {"artifact": name, "reason": "digest_mismatch", "expected": expected, "actual": actual}
            )
    return failures


def verify_package(path: Path) -> int:
    manifest, _ = _manifest(path)
    missing = []
    artifacts = manifest.get("artifacts", manifest.get("contents", {}))
    for name in artifacts.values():
        if not (path / name).is_file():
            missing.append(name)
    if missing:
        print(json.dumps({"status": "failed", "missing": missing}, indent=2))
        return 1
    if not manifest.get("knowledge_not_memory", False):
        print(json.dumps({"status": "failed", "reason": "package is not marked knowledge_not_memory"}, indent=2))
        return 1
    records = path / artifacts.get("records", "records.jsonl")
    embedding_index_name = artifacts.get("embedding_index")
    embeddings = path / artifacts.get("embeddings", "embeddings.jsonl")
    with records.open(encoding="utf-8") as stream:
        record_count = sum(1 for line in stream if line.strip())
    if embedding_index_name:
        with (path / embedding_index_name).open(encoding="utf-8") as stream:
            embedding_count = sum(1 for line in stream if line.strip())
    else:
        with embeddings.open(encoding="utf-8") as stream:
            embedding_count = sum(1 for line in stream if line.strip())
    counts_agree = record_count == embedding_count == manifest.get("records")

    digests, digest_source = _declared_digests(path, manifest)
    if not digests:
        print(
            json.dumps(
                {"status": "failed", "reason": "no artifact digests declared", "package_id": manifest.get("package_id")},
                indent=2,
            )
        )
        return 1
    digest_failures = _verify_digests(path, digests)

    # Every artifact the manifest names must be covered by a digest, or a file
    # could be swapped without any check noticing it was never verified. Two are
    # structurally exempt: a checksums file cannot contain its own digest, and a
    # signature cannot be inside the thing it signs.
    self_referential = {artifacts.get("checksums"), artifacts.get("signature")}
    unverified = sorted(set(artifacts.values()) - set(digests) - self_referential - {None})

    # Retrieval-geometry report. One vector per record means text past the
    # embedding window is unreachable by search; this counts how much of the
    # package is in that condition without failing the package for it.
    oversized = 0
    longest = 0
    with records.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            length = len(json.loads(line).get("text", ""))
            longest = max(longest, length)
            if length > _EMBEDDING_WINDOW_CHARS:
                oversized += 1

    result = {
        "status": "passed" if counts_agree and not digest_failures and not unverified else "failed",
        "package_id": manifest.get("package_id"),
        "records": record_count,
        "embeddings": embedding_count,
        "embedding_model": manifest.get("embedding", {}).get("model"),
        "digest_source": digest_source,
        "digests_verified": len(digests),
        "signature_covers_digests": digest_source == "manifest",
        "retrieval_geometry": {
            "assumed_window_chars": _EMBEDDING_WINDOW_CHARS,
            "records_exceeding_window": oversized,
            "longest_record_chars": longest,
        },
    }
    if digest_failures:
        result["digest_failures"] = digest_failures
    if unverified:
        result["artifacts_without_digests"] = unverified
    if oversized:
        result["warning"] = (
            f"{oversized} of {record_count} records exceed the embedding window; "
            "their vectors represent only the opening of each record and search cannot reach the rest"
        )
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 1


def _safe_component(value: str) -> str:
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise SystemExit(f"unsafe package component: {value!r}")
    return value


def _package_version(manifest: dict) -> str:
    return _safe_component(str(manifest.get("version") or manifest["package_id"]))


def install_package(path: Path, root: Path) -> int:
    manifest, _ = _manifest(path)
    if verify_package(path) != 0:
        return 1
    package_id = _safe_component(manifest["package_id"])
    version = _package_version(manifest)
    package_root = root.expanduser().resolve() / package_id
    versions_root = package_root / "versions"
    destination = versions_root / version
    root.mkdir(parents=True, exist_ok=True)
    versions_root.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    staging = Path(tempfile.mkdtemp(prefix=f".{version}.", dir=versions_root))
    try:
        shutil.copytree(path, staging / "package", dirs_exist_ok=True)
        (staging / "install.json").write_text(
            json.dumps({"package_id": package_id, "version": version, "source": str(path.resolve())}, indent=2) + "\n",
            encoding="utf-8",
        )
        staging.rename(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    active = package_root / "active"
    temporary_link = package_root / ".active.tmp"
    temporary_link.unlink(missing_ok=True)
    temporary_link.symlink_to(Path("versions") / version, target_is_directory=True)
    temporary_link.replace(active)
    print(json.dumps({"status": "installed", "package_id": package_id, "version": version, "path": str(active)}, indent=2))
    return 0


def rollback_package(package_id: str, version: str, root: Path) -> int:
    package_id = _safe_component(package_id)
    version = _safe_component(version)
    package_root = root.expanduser().resolve() / package_id
    destination = package_root / "versions" / version
    if not destination.is_dir():
        print(json.dumps({"status": "failed", "reason": "version_not_installed", "package_id": package_id, "version": version}, indent=2))
        return 1
    active = package_root / "active"
    temporary_link = package_root / ".active.tmp"
    temporary_link.unlink(missing_ok=True)
    temporary_link.symlink_to(Path("versions") / version, target_is_directory=True)
    temporary_link.replace(active)
    print(json.dumps({"status": "rolled_back", "package_id": package_id, "version": version, "path": str(active)}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lore")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("inspect", "verify"):
        sub = subparsers.add_parser(command)
        sub.add_argument("package", type=Path)
    install = subparsers.add_parser("install")
    install.add_argument("package", type=Path)
    install.add_argument("--root", type=Path, default=Path("~/.lore/collections"))
    rollback = subparsers.add_parser("rollback")
    rollback.add_argument("package_id")
    rollback.add_argument("--to", required=True, dest="version")
    rollback.add_argument("--root", type=Path, default=Path("~/.lore/collections"))

    args = parser.parse_args(argv)
    if args.command == "inspect":
        return inspect_package(args.package)
    if args.command == "verify":
        return verify_package(args.package)
    if args.command == "install":
        return install_package(args.package, args.root)
    if args.command == "rollback":
        return rollback_package(args.package_id, args.version, args.root)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
