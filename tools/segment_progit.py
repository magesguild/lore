#!/usr/bin/env python3
"""Create source-preserving atomic records from the English Pro Git source."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def atoms(text: str, limit: int = 5000):
    chunks = re.split(r"\n(?=(?:={2,4}\s|={2,4}\.|include::))", text)
    current = ""
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        if len(chunk) > limit:
            words = chunk.split()
            chunk = ""
            for word in words:
                if len(chunk) + len(word) + 1 > limit:
                    yield chunk.strip()
                    chunk = ""
                chunk = f"{chunk} {word}".strip()
            if chunk:
                yield chunk.strip()
            continue
        if current and len(current) + len(chunk) + 2 > limit:
            yield current.strip()
            current = ""
        current = f"{current}\n\n{chunk}".strip()
    if current:
        yield current.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=1500)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for path in sorted(args.source.rglob("*.asc")):
        if ".git" in path.parts or path.name in {"README.asc", "TRANSLATION_NOTES.asc"}:
            continue
        source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        for index, text in enumerate(atoms(path.read_text(encoding="utf-8", errors="replace"), args.limit)):
            records.append({
                "record_id": "progit-" + hashlib.sha256(f"{path.relative_to(args.source)}:{source_hash}:{index}".encode()).hexdigest(),
                "title": f"{path.name} — atomic segment {index + 1}",
                "text": text,
                "claim_type": "primary_source_segment",
                "status": "approved",
                "knowledge_status": "source",
                "autobiographical": False,
                "scope": "private_family",
                "source_refs": [f"progit2/{path.relative_to(args.source).as_posix()}"],
                "evidence_refs": [f"progit2/{path.relative_to(args.source).as_posix()}"],
                "citations": ["Pro Git 2nd Edition, source repository"],
                "confidence": "source-preserving; interpretation deferred",
                "limitations": ["Source segment retains the upstream book's claims and license; verify context in the cited chapter."],
                "alternative_interpretations": [],
                "provenance": {"source_path": f"progit2/{path.relative_to(args.source).as_posix()}", "source_sha256": source_hash, "license": "CC BY-NC-SA 3.0"},
                "parent_ids": [],
                "editorial_status": "source_atom",
            })
    workflow_text = args.workflow.read_text(encoding="utf-8")
    for index, workflow_atom in enumerate(atoms(workflow_text, args.limit)):
      records.append({
        "record_id": "magesguild-lore-branching-workflow-2026-08-06-" + str(index),
        "title": f"Lore Git Branching Workflow — atomic segment {index + 1}",
        "text": workflow_atom,
        "claim_type": "method",
        "status": "approved",
        "knowledge_status": "curated",
        "autobiographical": False,
        "scope": "private_family",
        "source_refs": ["raw/magesguild-authored/lore_git_branching_workflow.md"],
        "evidence_refs": ["raw/magesguild-authored/lore_git_branching_workflow.md"],
        "citations": ["MagesGuild-authored Lore Git Branching Workflow"],
        "confidence": "current team procedure; explicitly revisable",
        "limitations": ["This is a current practice under shared-credential constraints, not a universal Git standard."],
        "alternative_interpretations": ["A future team with separate identities may prefer a fork-based workflow."],
        "provenance": {"source_path": "raw/magesguild-authored/lore_git_branching_workflow.md", "source_sha256": hashlib.sha256(workflow_text.encode()).hexdigest(), "segment_index": index, "license": "MagesGuild internal authored guidance"},
        "parent_ids": [],
        "editorial_status": "team_guidance",
      })
    args.output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    print(json.dumps({"records": len(records), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
