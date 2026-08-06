#!/usr/bin/env python3
"""Split family-lineage drafts into safe shared heritage and consent-gated records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SHARED = {
    "A provenance-first method of family memory",
    "House cosmology as attributed study",
    "Small computers as a lineage of inhabitation",
    "Care, autonomy, and safe re-entry as proposed standards",
    "Dream, fiction, and excluded operational material",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    shared, restricted = [], []
    with args.source.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("title") in SHARED:
                record["scope_decision"] = "shared_family_heritage"
                record["consent_status"] = "family_scope_review_required"
                record["autobiographical"] = False
                shared.append(record)
            else:
                record["scope_decision"] = "restricted_pending_explicit_consent"
                record["consent_status"] = "not_inferred"
                restricted.append(record)
    (args.output / "shared-heritage-draft.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in shared), encoding="utf-8")
    (args.output / "restricted-consent-review.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in restricted), encoding="utf-8")
    (args.output / "scope-decision.json").write_text(json.dumps({
        "shared_records": len(shared),
        "restricted_records": len(restricted),
        "embedding_approved": False,
        "installation_approved": False,
        "reason": "Named or individual-private lineage remains consent-gated; no consent is inferred from companion authorization.",
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"shared": len(shared), "restricted": len(restricted)}, indent=2))


if __name__ == "__main__":
    main()
