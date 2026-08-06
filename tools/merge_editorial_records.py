#!/usr/bin/env python3
"""Merge reviewed editorial records without losing parent provenance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED = {"record_id", "text", "claim_type", "status", "evidence_refs", "citations", "provenance"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("drafts", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--require-status", default="approved")
    args = parser.parse_args()
    accepted = []
    rejected = []
    with args.drafts.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            missing = sorted(REQUIRED - record.keys())
            if missing or record.get("status") != args.require_status or record.get("autobiographical", False):
                rejected.append({"line": line_number, "record_id": record.get("record_id"), "missing": missing, "reason": "not-approved-or-invalid"})
                continue
            record["editorial_status"] = "accepted_for_embedding"
            accepted.append(record)
    args.output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in accepted), encoding="utf-8")
    (args.output.with_suffix(args.output.suffix + ".rejections.jsonl")).write_text("".join(json.dumps(r) + "\n" for r in rejected), encoding="utf-8")
    print(json.dumps({"accepted": len(accepted), "rejected": len(rejected), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
