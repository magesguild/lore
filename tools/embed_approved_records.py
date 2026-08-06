#!/usr/bin/env python3
"""Embed approved editorial records into an isolated staging artifact."""

from __future__ import annotations

import argparse
import json
import struct
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def embed(texts: list[str], model: str) -> list[list[float]]:
    payload = json.dumps({"model": model, "input": texts}).encode()
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)["embeddings"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("records", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model", default="mxbai-embed-large:latest")
    args = parser.parse_args()
    records = [json.loads(line) for line in args.records.open(encoding="utf-8") if line.strip()]
    vectors = embed([record["text"] for record in records], args.model)
    args.output.mkdir(parents=True, exist_ok=True)
    vector_path = args.output / "embeddings.f32"
    index_path = args.output / "embedding_index.jsonl"
    with vector_path.open("wb") as vector_file, index_path.open("w", encoding="utf-8") as index_file:
        for row, (record, vector) in enumerate(zip(records, vectors)):
            offset = vector_file.tell()
            vector_file.write(struct.pack(f"<{len(vector)}f", *vector))
            index_file.write(json.dumps({"record_id": record["record_id"], "row": row, "byte_offset": offset}) + "\n")
    manifest = {
        "status": "staging_only",
        "records": len(records),
        "model": args.model,
        "dimensions": len(vectors[0]) if vectors else 0,
        "dtype": "float32",
        "endianness": "little",
        "source_records": str(args.records),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "memory_installation": False,
    }
    (args.output / "embedding_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
