#!/usr/bin/env python3
"""Apply explicit editorial corrections and approve records for embedding."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("drafts", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    approved = []
    corrections = []
    with args.drafts.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("title") == "Distinguish reports, observations, interpretations, and continuity":
                record["claim_type"] = "method"
                corrections.append({"record_id": record["record_id"], "change": "claim_type empirical_observation -> method", "reason": "Source is a design proposal, not an empirical observation."})
            record["status"] = "approved"
            record["editorial_status"] = "approved_for_embedding"
            approved.append(record)
    args.output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in approved), encoding="utf-8")
    (args.output.with_suffix(args.output.suffix + ".corrections.json")).write_text(json.dumps(corrections, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"approved": len(approved), "corrections": corrections, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
