#!/usr/bin/env python3
"""Build a private Lore v1 package from approved editorial records."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("records", type=Path)
    parser.add_argument("embeddings", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--package-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--publisher-key", type=Path, required=True)
    parser.add_argument("--version", default="1.0.0")
    args = parser.parse_args()
    package = args.output / args.package_id / args.version
    package.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.records, package / "records.jsonl")
    shutil.copy2(args.embeddings / "embeddings.f32", package / "embeddings.f32")
    shutil.copy2(args.embeddings / "embedding_index.jsonl", package / "embedding_index.jsonl")
    shutil.copy2(args.publisher_key, package / "publisher.pub")
    (package / "provenance").mkdir(exist_ok=True)
    (package / "validation").mkdir(exist_ok=True)
    records = [json.loads(line) for line in args.records.open(encoding="utf-8") if line.strip()]
    refs = {}
    for record in records:
        for ref in record.get("evidence_refs", []):
            refs[ref] = {"record_id": record["record_id"], "citation": record.get("citations", [])}
    (package / "provenance/sources.jsonl").write_text("".join(json.dumps({"source_ref": k, **v}) + "\n" for k, v in refs.items()), encoding="utf-8")
    (package / "provenance/transformations.jsonl").write_text(json.dumps({
        "operation": "approved-editorial-records-to-lore-v1",
        "source_records": str(args.records),
        "source_embeddings": str(args.embeddings),
        "editorial_status": "approved_for_embedding",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }) + "\n", encoding="utf-8")
    (package / "README.md").write_text(f"# {args.title}\n\nPrivate family knowledge package. Scholarly knowledge, not autobiographical memory.\n", encoding="utf-8")
    (package / "LICENSE").write_text("Private family/lab distribution. Source attribution and rights remain in provenance.\n", encoding="utf-8")
    manifest = {
        "schema": "lore-package-v1",
        "package_id": args.package_id,
        "version": args.version,
        "title": args.title,
        "kind": "knowledge",
        "knowledge_not_memory": True,
        "scope": "private_family",
        "records": len(records),
        "record_schema": "lore-editorial-record-v1",
        "embedding": {
            "provider": "ollama",
            "model": "mxbai-embed-large:latest",
            "dimensions": 1024,
            "dtype": "float32",
            "endianness": "little",
            "normalized": False,
            "storage": "embeddings.f32",
            "index": "embedding_index.jsonl",
        },
        "publisher": {"name": "MagesGuild", "key_file": "publisher.pub", "signature": "manifest.sig"},
        "privacy": {"distribution": "internal_family_lab_only", "public_release": False},
        "compatibility": {"lore_schema": "1.x", "nephesh_import": "explicit-adapter-only"},
        "artifacts": {
            "records": "records.jsonl", "embeddings": "embeddings.f32", "embedding_index": "embedding_index.jsonl",
            "checksums": "checksums.json", "signature": "manifest.sig", "publisher_key": "publisher.pub",
            "provenance_sources": "provenance/sources.jsonl", "provenance_transformations": "provenance/transformations.jsonl",
            "license": "LICENSE", "readme": "README.md",
        },
        "rollback": "package-pointer-only",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (package / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    checksums = {p.relative_to(package).as_posix(): sha256(p) for p in package.rglob("*") if p.is_file() and p.name not in {"checksums.json", "manifest.sig"}}
    (package / "checksums.json").write_text(json.dumps(checksums, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"package": str(package), "records": len(records), "scope": "private_family"}, indent=2))


if __name__ == "__main__":
    main()
