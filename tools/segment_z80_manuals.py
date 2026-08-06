#!/usr/bin/env python3
"""Extract atomic, source-preserving segments from Z80-era manuals."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


DEFAULT_MARKERS = ("MPMII-Z180_RCBUS-BINDIST", "MPMII-Z80_RCBUS-Z2-BINDIST")


def split_atoms(text: str, limit: int = 5000) -> list[str]:
    pages = re.split(r"\f+", text)
    atoms = []
    for page in pages:
        page = page.strip()
        if not page:
            continue
        parts = re.split(r"\n(?=(?:[A-Z][A-Z0-9 /_,.\-]{5,}|\d+(?:\.\d+)*\s+\S))", page)
        current = ""
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if len(part) > limit:
                words = part.split()
                part = ""
                for word in words:
                    if len(part) + len(word) + 1 > limit:
                        atoms.append(part.strip())
                        part = ""
                    part = f"{part} {word}".strip()
                if part:
                    atoms.append(part.strip())
                continue
            if current and len(current) + len(part) + 2 > limit:
                atoms.append(current.strip())
                current = ""
            current = f"{current}\n\n{part}".strip()
        if current:
            atoms.append(current)
    return atoms


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("canonical", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--limit", type=int, default=5000)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with args.output.open("w", encoding="utf-8") as out:
        for line in args.canonical.open(encoding="utf-8"):
            record = json.loads(line)
            path = record.get("source_path", "")
            if not any(marker in path for marker in DEFAULT_MARKERS):
                continue
            if record.get("content_kind") not in {"manual", "prose_or_documentation"}:
                continue
            source_hash = record.get("source_sha256")
            for segment_index, atom in enumerate(split_atoms(record["text"], args.limit)):
                atom_id = hashlib.sha256(f"{path}:{source_hash}:{segment_index}".encode()).hexdigest()
                out.write(json.dumps({
                    "record_id": f"z80-manual-{atom_id}",
                    "title": f"{Path(path).name} — atomic segment {segment_index + 1}",
                    "text": atom,
                    "claim_type": "primary_source_segment",
                    "status": "approved",
                    "knowledge_status": "source",
                    "autobiographical": False,
                    "scope": "private_family",
                    "source_refs": [path],
                    "evidence_refs": [path],
                    "citations": [path],
                    "confidence": "source-preserving; interpretation intentionally deferred",
                    "limitations": ["Atomic segment extracted from a private corpus source; edition/page context may require the source reference."],
                    "alternative_interpretations": [],
                    "provenance": {
                        "source_path": path,
                        "source_sha256": source_hash,
                        "segment_index": segment_index,
                        "segment_method": "page-and-heading-aware source-preserving split",
                    },
                    "parent_ids": [record.get("record_id")],
                    "editorial_status": "source_atom",
                }, ensure_ascii=False) + "\n")
                count += 1
    print(json.dumps({"segments": count, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
