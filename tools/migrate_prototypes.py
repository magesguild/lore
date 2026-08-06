#!/usr/bin/env python3
"""Migrate prototype Lore packages into the finalized v1 on-disk format."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path


PACKAGE_IDS = {
    "nephesh-5.0-awareness-2026-08-05": "org.magesguild.nephesh.awareness",
    "magesguild-cosmology-2026-08-06": "org.magesguild.cosmology",
    "magesguild-qualia-research-2026-08-06": "org.magesguild.qualia-research",
    "magesguild-z80-computing-2026-08-06": "org.magesguild.z80-computing",
    "magesguild-git-workflow-2026-08-06": "org.magesguild.git-workflow",
    "magesguild-harness-continuity-2026-08-06": "org.magesguild.harness-continuity",
    "magesguild-qualiant-awareness-2026-08-06": "org.magesguild.qualiant-awareness",
    "magesguild-research-methodology-2026-08-06": "org.magesguild.research-methodology",
    "magesguild-creative-language-2026-08-06": "org.magesguild.creative-language",
    "magesguild-training-practice-2026-08-06": "org.magesguild.training-practice",
    "magesguild-family-lineage-2026-08-06": "org.magesguild.family-lineage",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def jsonl(path: Path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def migrate(source: Path, output: Path, publisher_key: Path) -> dict:
    old = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    package_id = PACKAGE_IDS[source.name]
    package = output / package_id / "1.0.0"
    package.mkdir(parents=True, exist_ok=True)
    records = []
    source_refs = {}
    for record in jsonl(source / "records.jsonl"):
        record = dict(record)
        source_path = record.get("source_path", "unknown")
        ref_id = hashlib.sha256(source_path.encode()).hexdigest()
        record["source_refs"] = [ref_id]
        record["knowledge_status"] = record.get("knowledge_status", "derived")
        record["autobiographical"] = False
        record["scope"] = old.get("package_scope", "generalized")
        record["provenance"] = {
            "source_path": source_path,
            "source_sha256": record.get("source_sha256"),
            "source_documents": record.get("source_documents", []),
            "source_version": record.get("document_date", old.get("built_at")),
            "curation_method": record.get("curation_method", "prototype migration"),
            "uncertainty": record.get("historical_status", "unknown"),
        }
        for key in ("source_path", "source_documents"):
            if isinstance(record.get(key), str):
                record[key] = record[key].replace("/home/thalia/", "")
        records.append(record)
        source_refs[ref_id] = {"source_path": source_path, "source_sha256": record.get("source_sha256")}

    records_path = package / "records.jsonl"
    records_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")

    vectors_path = package / "embeddings.f32"
    index_path = package / "embedding_index.jsonl"
    with vectors_path.open("wb") as vectors, index_path.open("w", encoding="utf-8") as index:
        for row, vector in enumerate(jsonl(source / "embeddings.jsonl")):
            values = vector["embedding"]
            offset = vectors.tell()
            vectors.write(struct.pack(f"<{len(values)}f", *values))
            index.write(json.dumps({"record_id": vector["record_id"], "row": row, "byte_offset": offset}) + "\n")

    (package / "provenance").mkdir(exist_ok=True)
    (package / "provenance/sources.jsonl").write_text("".join(json.dumps({"source_id": k, **v}) + "\n" for k, v in source_refs.items()), encoding="utf-8")
    (package / "provenance/transformations.jsonl").write_text(json.dumps({
        "operation": "prototype-to-lore-v1",
        "source_package": source.name,
        "source_manifest_sha256": sha256(source / "manifest.json"),
        "genericization_preserved": True,
        "embedding_conversion": "JSONL float vectors to little-endian float32 matrix",
        "performed_at": datetime.now(timezone.utc).isoformat(),
    }) + "\n", encoding="utf-8")
    (package / "validation").mkdir(exist_ok=True)
    (package / "README.md").write_text(f"# {old.get('title', package_id)}\n\nLore v1 package for Clio's knowledge collections.\n\nThis package is knowledge, not autobiographical memory.\n", encoding="utf-8")
    (package / "LICENSE").write_text("Package redistribution terms are declared in manifest.json and source provenance.\n", encoding="utf-8")

    # The publisher key must exist before the manifest is written, because the
    # manifest now carries a digest of it.
    shutil.copy2(publisher_key, package / "publisher.pub")

    artifacts = {
        "records": "records.jsonl",
        "embeddings": "embeddings.f32",
        "embedding_index": "embedding_index.jsonl",
        "checksums": "checksums.json",
        "signature": "manifest.sig",
        "publisher_key": "publisher.pub",
        "provenance_sources": "provenance/sources.jsonl",
        "provenance_transformations": "provenance/transformations.jsonl",
        "license": "LICENSE",
        "readme": "README.md",
    }

    # Digests go INSIDE the manifest, because the manifest is what the
    # signature covers. Carried only in a sidecar checksums.json they are
    # unsigned: an edit to a payload file and its checksum entry together
    # leaves a signature over the manifest still valid, so the signature would
    # attest to a filename list and nothing about the bytes.
    # PACKAGE_FORMAT.md has required this from the start.
    #
    # Two artifacts are structurally excluded: checksums.json cannot contain
    # its own digest, and manifest.sig signs the manifest and so cannot be
    # inside it.
    self_referential = {artifacts["checksums"], artifacts["signature"]}
    artifact_digests = {
        name: sha256(package / name)
        for name in sorted(set(artifacts.values()) - self_referential)
        if (package / name).is_file()
    }

    manifest = {
        "schema": "lore-package-v1",
        "package_id": package_id,
        "version": "1.0.0",
        "title": old.get("title", package_id),
        "description": old.get("description", "MagesGuild curated knowledge collection"),
        "kind": "knowledge",
        "knowledge_not_memory": True,
        "scope": old.get("package_scope", "generalized"),
        "records": len(records),
        "record_schema": "lore-record-v1",
        "embedding": {
            "provider": old.get("embedding", {}).get("provider", "ollama"),
            "model": old.get("embedding", {}).get("model", "mxbai-embed-large:latest"),
            "dimensions": old.get("embedding", {}).get("dimensions", 1024),
            "dtype": "float32",
            "endianness": "little",
            "normalized": False,
            "storage": "embeddings.f32",
            "index": "embedding_index.jsonl",
        },
        "publisher": {"name": "MagesGuild", "key_file": "publisher.pub"},
        "license": {"package": "declared-in-manifest", "source_licenses": "see provenance"},
        "compatibility": {"lore_schema": "1.x", "nephesh_import": "explicit-adapter-only"},
        "artifacts": artifacts,
        "artifact_digests": artifact_digests,
        "migration": {"from": source.name, "source_manifest_sha256": sha256(source / "manifest.json")},
        "rollback": "package-pointer-only",
    }
    (package / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    # checksums.json is retained for tooling that predates artifact_digests. It
    # now also covers manifest.json, so a reader without signature support can
    # still detect a manifest edit.
    files = {p.relative_to(package).as_posix(): sha256(p) for p in package.rglob("*") if p.is_file() and p.name not in {"checksums.json", "manifest.sig"}}
    (package / "checksums.json").write_text(json.dumps(files, indent=2) + "\n", encoding="utf-8")
    # Signature is created by the caller after all package bytes are final.
    return {"package_id": package_id, "version": "1.0.0", "records": len(records), "path": str(package)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("packages"))
    parser.add_argument("--output", type=Path, default=Path("packages-v1"))
    parser.add_argument("--publisher-key", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for source_name in PACKAGE_IDS:
        source = args.source / source_name
        if source.is_dir():
            results.append(migrate(source, args.output, args.publisher_key))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
