#!/usr/bin/env python3
"""Normalize richer editorial drafts into the portable Lore record shape."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    normalized = []
    with args.source.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            source = json.loads(line)
            if "claim_type" in source:
                record = source
            else:
                record = {
                    "record_id": source["record_id"],
                    "title": source.get("title"),
                    "text": source["text"],
                    "claim_type": "interpretation",
                    "status": source.get("status", "draft"),
                    "evidence_refs": source.get("source_task_ids", []) + source.get("parent_ids", []),
                    "citations": source.get("evidence", []),
                    "confidence": "moderate; source and rights review remain open",
                    "limitations": source.get("limitations", []),
                    "alternative_interpretations": source.get("interpretations", []),
                    "provenance": {
                        "editorial_record_type": source.get("record_type"),
                        "authored_testimony": source.get("authored_testimony", []),
                        "factual_claims": source.get("factual_claims", []),
                        "attribution_and_rights": source.get("attribution_and_rights"),
                        "privacy_note": source.get("privacy_note"),
                        "review_notes": source.get("review_notes", []),
                    },
                    "parent_ids": source.get("parent_ids", []),
                    "autobiographical": False,
                    "scope": source.get("scope", "generalized"),
                }
            record["status"] = "approved"
            record["editorial_status"] = "approved_for_embedding"
            record["autobiographical"] = False
            normalized.append(record)
    args.output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in normalized), encoding="utf-8")
    print(json.dumps({"records": len(normalized), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
