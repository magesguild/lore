#!/usr/bin/env python3
"""Embed approved editorial records into an isolated staging artifact.

Records are chunked before embedding. The embedding model reads a bounded
window; text past it is not represented by the vector and retrieval cannot
reach it. Sending a whole record and accepting whatever comes back produces
vectors that look healthy and describe only each record's opening — three
unrelated multi-megabyte files in an earlier package shared one identical
vector for exactly this reason.

The embedding request sets truncate=false so the model REFUSES over-long input
instead of silently shortening it. A failed dependency must not become a false
success: if this raises, the package is not built, which is the correct
outcome.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lore.chunking import CHUNK_OVERLAP, CHUNK_SIZE, MEASURED_WINDOW, chunk_record  # noqa: E402

EMBED_URL = "http://127.0.0.1:11434/api/embed"

# Batch so one enormous request neither times out nor hides which chunk failed.
BATCH = 64


def embed(texts: list[str], model: str) -> list[list[float]]:
    """Embed a batch, refusing truncation.

    truncate=false makes the server return HTTP 400 for input beyond its
    window rather than returning a vector computed from the opening. That is
    the difference between a build that fails and a package that lies.
    """
    payload = json.dumps({"model": model, "input": texts, "truncate": False}).encode()
    request = urllib.request.Request(
        EMBED_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.load(response)["embeddings"]
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:400]
        longest = max((len(t) for t in texts), default=0)
        raise SystemExit(
            f"embedding refused (HTTP {error.code}): {detail}\n"
            f"longest text in batch: {longest} characters; measured model window is "
            f"{MEASURED_WINDOW}. Chunking is misconfigured — no package written."
        ) from error
    except urllib.error.URLError as error:
        raise SystemExit(f"embedding endpoint unreachable at {EMBED_URL}: {error.reason}") from error


def embed_all(texts: list[str], model: str) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH):
        vectors.extend(embed(texts[start : start + BATCH], model))
    if len(vectors) != len(texts):
        raise SystemExit(f"embedding returned {len(vectors)} vectors for {len(texts)} chunks")
    return vectors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("records", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model", default="mxbai-embed-large:latest")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument("--chunk-overlap", type=int, default=CHUNK_OVERLAP)
    args = parser.parse_args()

    records = [json.loads(line) for line in args.records.open(encoding="utf-8") if line.strip()]

    chunks: list[dict] = []
    for record in records:
        chunks.extend(chunk_record(record, args.chunk_size, args.chunk_overlap))
    if not chunks:
        raise SystemExit("no chunks to embed")

    vectors = embed_all([chunk["text"] for chunk in chunks], args.model)

    args.output.mkdir(parents=True, exist_ok=True)
    vector_path = args.output / "embeddings.f32"
    index_path = args.output / "embedding_index.jsonl"
    with vector_path.open("wb") as vector_file, index_path.open("w", encoding="utf-8") as index_file:
        for row, (chunk, vector) in enumerate(zip(chunks, vectors)):
            offset = vector_file.tell()
            vector_file.write(struct.pack(f"<{len(vector)}f", *vector))
            index_file.write(
                json.dumps(
                    {
                        "record_id": chunk["record_id"],
                        "chunk_index": chunk["chunk_index"],
                        "chunk_count": chunk["chunk_count"],
                        "row": row,
                        "byte_offset": offset,
                        "chars": len(chunk["text"]),
                    }
                )
                + "\n"
            )

    manifest = {
        "status": "staging_only",
        "records": len(records),
        "chunks": len(chunks),
        "model": args.model,
        "dimensions": len(vectors[0]) if vectors else 0,
        "dtype": "float32",
        "endianness": "little",
        "chunking": {
            "chunk_size": args.chunk_size,
            "overlap": args.chunk_overlap,
            "measured_window": MEASURED_WINDOW,
            "truncation": "refused",
        },
        "source_records": str(args.records),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "memory_installation": False,
    }
    (args.output / "embedding_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
