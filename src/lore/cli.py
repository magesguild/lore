from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import io
import json
import os
import stat
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .chunking import MEASURED_WINDOW
from .signing import SignatureError, verify_manifest


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


def _safe_relative(package: Path, name: object) -> Path:
    """Resolve an artifact path without allowing it to escape the package."""
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise SystemExit(f"unsafe package artifact path: {name!r}")
    target = (package / name).resolve()
    root = package.resolve()
    if target != root and root not in target.parents:
        raise SystemExit(f"package artifact escapes package root: {name!r}")
    return target


def _artifact_names(manifest: dict) -> dict[str, str]:
    artifacts = manifest.get("artifacts", manifest.get("contents", {}))
    if not isinstance(artifacts, dict):
        raise SystemExit("manifest artifacts must be an object")
    return {str(role): name for role, name in artifacts.items()}


def _artifact_path(package: Path, manifest: dict, role: str, default: str) -> Path:
    return _safe_relative(package, _artifact_names(manifest).get(role, default))


def _ensure_directory(path: Path) -> None:
    if path.is_symlink():
        raise SystemExit(f"refusing symlinked Lore directory: {path}")
    if path.exists() and not path.is_dir():
        raise SystemExit(f"Lore path is not a directory: {path}")
    path.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise SystemExit(f"refusing symlinked Lore directory: {path}")


def _validate_package_tree(package: Path, manifest: dict) -> None:
    """Reject symlinks, special files, and unmanifested payloads."""
    artifact_names = _artifact_names(manifest)
    for name in artifact_names.values():
        _safe_relative(package, name)
    allowed = {"manifest.json", *artifact_names.values()}
    for entry in package.rglob("*"):
        relative = entry.relative_to(package).as_posix()
        if entry.is_symlink():
            raise SystemExit(f"package contains a symlink: {relative}")
        mode = entry.lstat().st_mode
        if entry.is_dir():
            continue
        if not stat.S_ISREG(mode):
            raise SystemExit(f"package contains a non-regular file: {relative}")
        if relative not in allowed:
            raise SystemExit(f"package contains an unmanifested artifact: {relative}")


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextlib.contextmanager
def _package_lock(package_root: Path):
    _ensure_directory(package_root)
    lock_path = package_root / ".lifecycle.lock"
    with lock_path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _append_history(package_root: Path, event: dict) -> None:
    path = package_root / "history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    _fsync_directory(path.parent)


def _manifest_digest(package: Path) -> str:
    return _sha256(package / "manifest.json")


def inspect_package(path: Path) -> int:
    manifest, _ = _manifest(path)
    print(json.dumps(manifest, indent=2))
    return 0


# The measured content window of the embedding model — see lore.chunking for
# how it was established. Text beyond it is not represented by the vector, so
# retrieval is blind to it. Used for reporting, never for rejection: a package
# with over-long embedded units is importable, its retrieval simply cannot be
# trusted past what the model could read.
_EMBEDDING_WINDOW_CHARS = MEASURED_WINDOW


def _declared_digests(package: Path, manifest: dict) -> tuple[dict[str, str], str]:
    """Return the digests to verify against, and where they came from.

    PACKAGE_FORMAT.md requires SHA-256 hashes for every artifact in the manifest
    itself. That placement matters: the manifest is what the signature covers,
    so digests carried there are transitively signed. Digests carried only in a
    separate checksums.json are not — an edit to a payload file and its checksum
    entry leaves any signature over the manifest still valid.

    A sidecar checksum file may be present as a convenience report, but it is
    not accepted as the verification source: only manifest digests are covered
    by the Ed25519 signature and therefore sufficient for installation.
    """
    inline = manifest.get("artifact_digests")
    if isinstance(inline, dict) and inline:
        return {str(k): str(v) for k, v in inline.items()}, "manifest"

    # A sidecar checksum file is useful as a convenience report, but it is not
    # authenticated by the manifest signature. It is not sufficient for a
    # package to pass verification.
    return {}, "none"


def _verify_digests(package: Path, digests: dict[str, str]) -> list[dict[str, str]]:
    """Recompute every declared digest. Returns one entry per failure."""
    failures: list[dict[str, str]] = []
    for name, expected in sorted(digests.items()):
        target = _safe_relative(package, name)
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
    _validate_package_tree(path, manifest)
    missing = []
    artifacts = _artifact_names(manifest)
    for name in artifacts.values():
        if not _safe_relative(path, name).is_file():
            missing.append(name)
    if missing:
        print(json.dumps({"status": "failed", "missing": missing}, indent=2))
        return 1
    if not manifest.get("knowledge_not_memory", False):
        print(json.dumps({"status": "failed", "reason": "package is not marked knowledge_not_memory"}, indent=2))
        return 1
    artifacts = _artifact_names(manifest)
    signature_name = artifacts.get("signature")
    publisher_key_name = artifacts.get("publisher_key")
    if not signature_name or not publisher_key_name:
        print(json.dumps({"status": "failed", "reason": "signed manifest and publisher key are required"}, indent=2))
        return 1
    try:
        verify_manifest(
            path / "manifest.json",
            _safe_relative(path, signature_name),
            _safe_relative(path, publisher_key_name),
        )
    except (SignatureError, OSError, SystemExit) as exc:
        print(json.dumps({"status": "failed", "reason": f"signature verification failed: {exc}"}, indent=2))
        return 1
    records = _artifact_path(path, manifest, "records", "records.jsonl")
    embedding_index_name = artifacts.get("embedding_index")
    embeddings = _artifact_path(path, manifest, "embeddings", "embeddings.jsonl")
    with records.open(encoding="utf-8") as stream:
        record_count = sum(1 for line in stream if line.strip())
    if embedding_index_name:
        with _safe_relative(path, embedding_index_name).open(encoding="utf-8") as stream:
            embedding_count = sum(1 for line in stream if line.strip())
    else:
        with embeddings.open(encoding="utf-8") as stream:
            embedding_count = sum(1 for line in stream if line.strip())
    # A chunked package embeds one vector per chunk, so embeddings legitimately
    # outnumber records. An unchunked package embeds one vector per record and
    # the counts must agree exactly.
    declared_chunks = manifest.get("chunks")
    if declared_chunks is not None:
        counts_agree = record_count == manifest.get("records") and embedding_count == declared_chunks
    else:
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

    # Retrieval-geometry report. What matters is the size of the EMBEDDED unit,
    # not the record: a chunked package may hold arbitrarily long records and
    # still retrieve well, while an unchunked one is blind past each record's
    # opening. Reported, never fatal — such a package is importable, its
    # retrieval simply cannot be trusted past what the model could read.
    oversized = 0
    longest = 0
    if declared_chunks is not None and embedding_index_name:
        unit = "chunks"
        with _safe_relative(path, embedding_index_name).open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                length = json.loads(line).get("chars")
                if length is None:
                    continue
                longest = max(longest, length)
                if length > _EMBEDDING_WINDOW_CHARS:
                    oversized += 1
    else:
        unit = "records"
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
        "chunked": declared_chunks is not None,
        "retrieval_geometry": {
            "embedded_unit": unit,
            "assumed_window_chars": _EMBEDDING_WINDOW_CHARS,
            f"{unit}_exceeding_window": oversized,
            f"longest_{unit[:-1]}_chars": longest,
        },
    }
    if digest_failures:
        result["digest_failures"] = digest_failures
    if unverified:
        result["artifacts_without_digests"] = unverified
    if oversized:
        total = embedding_count if unit == "chunks" else record_count
        result["warning"] = (
            f"{oversized} of {total} embedded {unit} exceed the model's window; "
            f"their vectors represent only the opening of each and search cannot reach the rest"
        )
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 1


def _safe_verify(path: Path, *, quiet: bool = False) -> int:
    """Turn malformed package input into a controlled verification failure."""
    try:
        if quiet:
            with contextlib.redirect_stdout(io.StringIO()):
                return verify_package(path)
        return verify_package(path)
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError, SystemExit) as exc:
        if not quiet:
            print(json.dumps({"status": "failed", "reason": f"malformed package: {exc}"}, indent=2))
        return 1


def _safe_component(value: str) -> str:
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise SystemExit(f"unsafe package component: {value!r}")
    return value


def _package_version(manifest: dict) -> str:
    return _safe_component(str(manifest.get("version") or manifest["package_id"]))


def _set_active(package_root: Path, version: str, *, event: str, actor: str = "human", reason: str = "") -> None:
    versions_root = package_root / "versions"
    destination = versions_root / version
    if _verified_installed(package_root, version) is None:
        raise SystemExit(f"version is incomplete, corrupt, or mismatched: {version}")
    active = package_root / "active"
    previous = active.resolve().name if active.is_symlink() else None
    temporary_link = package_root / ".active.tmp"
    temporary_link.unlink(missing_ok=True)
    temporary_link.symlink_to(Path("versions") / version, target_is_directory=True)
    temporary_link.replace(active)
    _fsync_directory(package_root)
    _append_history(package_root, {
        "event": event,
        "package_id": package_root.name,
        "from_version": previous,
        "to_version": version,
        "actor": actor,
        "reason": reason,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })


def _installed_manifest(destination: Path) -> tuple[dict, str] | None:
    package = destination / "package"
    manifest_path = package / "manifest.json"
    if not manifest_path.is_file():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return manifest, _manifest_digest(package)


def _verified_installed(package_root: Path, version: str) -> tuple[dict, str] | None:
    destination = package_root / "versions" / version
    installed = _installed_manifest(destination)
    if installed is None:
        return None
    manifest, digest = installed
    if str(manifest.get("package_id")) != package_root.name or str(manifest.get("version")) != version:
        return None
    if _safe_verify(destination / "package", quiet=True) != 0:
        return None
    return manifest, digest


def install_package(path: Path, root: Path, *, activate: bool = False) -> int:
    manifest, _ = _manifest(path)
    if _safe_verify(path) != 0:
        return 1
    package_id = _safe_component(str(manifest["package_id"]))
    version = _package_version(manifest)
    package_root = root.expanduser().resolve() / package_id
    versions_root = package_root / "versions"
    destination = versions_root / version
    with _package_lock(package_root):
        _ensure_directory(root.expanduser().resolve())
        _ensure_directory(versions_root)
        incoming_digest = _manifest_digest(path)
        if destination.exists():
            installed = _verified_installed(package_root, version)
            if installed and installed[1] == incoming_digest:
                if activate:
                    _set_active(package_root, version, event="activate", reason="idempotent install")
                print(json.dumps({
                    "status": "already_installed",
                    "activated": activate,
                    "package_id": package_id,
                    "version": version,
                    "path": str(package_root / "active" if activate else destination),
                }, indent=2))
                return 0
            if installed is None:
                raise SystemExit(f"installed version {package_id} {version} is incomplete or corrupt")
            raise SystemExit(f"version {package_id} {version} is already installed with different bytes")
        staging = Path(tempfile.mkdtemp(prefix=f".{version}.", dir=versions_root))
        try:
            shutil.copytree(path, staging / "package", dirs_exist_ok=True)
            if _safe_verify(staging / "package", quiet=True) != 0:
                raise SystemExit("staged package failed verification after copying")
            (staging / "install.json").write_text(
                json.dumps({
                    "package_id": package_id,
                    "version": version,
                    "manifest_sha256": incoming_digest,
                    "source": str(path.resolve()),
                    "installed_at": datetime.now(timezone.utc).isoformat(),
                }, indent=2) + "\n",
                encoding="utf-8",
            )
            _fsync_directory(staging)
            staging.rename(destination)
            _fsync_directory(versions_root)
            _append_history(package_root, {
                "event": "install",
                "package_id": package_id,
                "version": version,
                "actor": "human",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        if activate:
            _set_active(package_root, version, event="activate", reason="install --activate")
    print(json.dumps({
        "status": "installed",
        "activated": activate,
        "package_id": package_id,
        "version": version,
        "path": str(package_root / "active" if activate else destination),
    }, indent=2))
    return 0


def rollback_package(package_id: str, version: str, root: Path) -> int:
    package_id = _safe_component(package_id)
    version = _safe_component(version)
    package_root = root.expanduser().resolve() / package_id
    destination = package_root / "versions" / version
    if not destination.is_dir():
        print(json.dumps({"status": "failed", "reason": "version_not_installed", "package_id": package_id, "version": version}, indent=2))
        return 1
    with _package_lock(package_root):
        if _installed_manifest(destination) is None:
            raise SystemExit(f"installed version is incomplete: {version}")
        _set_active(package_root, version, event="rollback", reason="explicit rollback")
    print(json.dumps({"status": "rolled_back", "package_id": package_id, "version": version, "path": str(package_root / "active")}, indent=2))
    return 0


def activate_package(package_id: str, version: str, root: Path) -> int:
    package_id = _safe_component(package_id)
    version = _safe_component(version)
    package_root = root.expanduser().resolve() / package_id
    with _package_lock(package_root):
        destination = package_root / "versions" / version
        installed = _verified_installed(package_root, version)
        if installed is None:
            raise SystemExit(f"installed version is incomplete: {version}")
        _set_active(package_root, version, event="activate", reason="explicit activation")
    print(json.dumps({"status": "activated", "package_id": package_id, "version": version}, indent=2))
    return 0


def history_package(package_id: str, root: Path) -> int:
    package_id = _safe_component(package_id)
    package_root = root.expanduser().resolve() / package_id
    history = package_root / "history.jsonl"
    if not history.is_file():
        print(json.dumps({"package_id": package_id, "events": []}, indent=2))
        return 0
    events = [json.loads(line) for line in history.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(json.dumps({"package_id": package_id, "events": events}, indent=2))
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
    install.add_argument("--activate", action="store_true", help="activate after verified installation")
    activate = subparsers.add_parser("activate")
    activate.add_argument("package_id")
    activate.add_argument("--to", required=True, dest="version")
    activate.add_argument("--root", type=Path, default=Path("~/.lore/collections"))
    rollback = subparsers.add_parser("rollback")
    rollback.add_argument("package_id")
    rollback.add_argument("--to", required=True, dest="version")
    rollback.add_argument("--root", type=Path, default=Path("~/.lore/collections"))
    history = subparsers.add_parser("history")
    history.add_argument("package_id")
    history.add_argument("--root", type=Path, default=Path("~/.lore/collections"))

    args = parser.parse_args(argv)
    if args.command == "inspect":
        return inspect_package(args.package)
    if args.command == "verify":
        return _safe_verify(args.package)
    if args.command == "install":
        return install_package(args.package, args.root, activate=args.activate)
    if args.command == "activate":
        return activate_package(args.package_id, args.version, args.root)
    if args.command == "rollback":
        return rollback_package(args.package_id, args.version, args.root)
    if args.command == "history":
        return history_package(args.package_id, args.root)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
