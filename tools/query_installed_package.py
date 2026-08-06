#!/usr/bin/env python3
"""Query an installed Lore package without touching Nephesh."""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lore.chunking import MEASURED_WINDOW  # noqa: E402


def embed(query: str, model: str) -> list[float]:
    # truncate=false for the same reason the builder sets it: a query longer
    # than the model's window would otherwise be silently shortened and
    # searched as its opening, returning confident results for a question that
    # was never asked in full.
    payload = json.dumps({"model": model, "input": query, "truncate": False}).encode()
    request = urllib.request.Request("http://127.0.0.1:11434/api/embed", data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response)["embeddings"][0]
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:200]
        raise SystemExit(
            f"query embedding refused (HTTP {error.code}): {detail}\n"
            f"query is {len(query)} characters; the model reads about {MEASURED_WINDOW}."
        ) from error
    except urllib.error.URLError as error:
        raise SystemExit(f"embedding endpoint unreachable: {error.reason}") from error


def cosine(a: list[float], b: list[float]) -> float:
    numerator = sum(x * y for x, y in zip(a, b))
    denom = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return numerator / denom if denom else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    manifest = json.loads((args.package / "manifest.json").read_text(encoding="utf-8"))
    model = manifest["embedding"]["model"]
    dimensions = manifest["embedding"]["dimensions"]
    records = [json.loads(line) for line in (args.package / manifest["artifacts"]["records"]).open(encoding="utf-8") if line.strip()]
    index = [json.loads(line) for line in (args.package / manifest["artifacts"]["embedding_index"]).open(encoding="utf-8") if line.strip()]
    vectors = []
    with (args.package / manifest["artifacts"]["embeddings"]).open("rb") as stream:
        for row in index:
            stream.seek(row["byte_offset"])
            values = struct.unpack(f"<{dimensions}f", stream.read(dimensions * 4))
            vectors.append((row["record_id"], list(values)))
    query_vector = embed(args.query, model)
    by_id = {record["record_id"]: record for record in records}
    results = sorted(((cosine(query_vector, vector), by_id[record_id]) for record_id, vector in vectors), key=lambda item: item[0], reverse=True)
    print(json.dumps({"package_id": manifest["package_id"], "query": args.query, "results": [{"score": score, "record": record} for score, record in results[:args.limit]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
