#!/usr/bin/env python3
"""Split long approved editorial records into provenance-linked atoms."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def chunks(text: str, limit: int) -> list[str]:
    pieces = re.split(r"\n\s*\n+", text)
    result, current = [], ""
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if len(piece) > limit:
            words = piece.split()
            piece = ""
            for word in words:
                if len(piece) + len(word) + 1 > limit:
                    result.append(piece.strip())
                    piece = ""
                piece = f"{piece} {word}".strip()
            if piece:
                result.append(piece.strip())
            continue
        if current and len(current) + len(piece) + 2 > limit:
            result.append(current.strip())
            current = ""
        current = f"{current}\n\n{piece}".strip()
    if current:
        result.append(current.strip())
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--limit", type=int, default=1500)
    args = parser.parse_args()
    output = []
    for line in args.source.open(encoding="utf-8"):
        if not line.strip():
            continue
        record = json.loads(line)
        atoms = chunks(record["text"], args.limit)
        for index, text in enumerate(atoms):
            item = dict(record)
            item["record_id"] = hashlib.sha256(f"{record['record_id']}:{index}".encode()).hexdigest()
            item["text"] = text
            item["parent_record_id"] = record["record_id"]
            item["atom_index"] = index
            item["atom_count"] = len(atoms)
            item["editorial_status"] = f"{record.get('editorial_status', 'approved')}:atomic_segment"
            output.append(item)
    args.output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in output), encoding="utf-8")
    print(json.dumps({"input": str(args.source), "output": str(args.output), "records": len(output), "limit": args.limit}, indent=2))


if __name__ == "__main__":
    main()
