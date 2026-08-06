"""Chunking for embedding, sized to the model's real content window.

A knowledge package ships one vector per embedded unit. If that unit is longer
than the embedding model can read, the vector represents only its opening and
retrieval is blind to everything after — silently, because the model returns a
normal-looking vector rather than an error.

This was not hypothetical. Measured on org.magesguild.z80-computing 1.0.0:
120 records produced only 115 distinct vectors. Three unrelated disk images of
67.8MB, 17.0MB and 8.5MB shared one byte-identical vector, because they share
an opening. Retrieval coverage for that package was 0.11% of its text.

WINDOW is measured, not assumed. Binary search against the live model, holding
a common prefix and varying only the tail: a marker at 1593 characters still
changed the vector, a marker at 1604 did not. CHUNK_SIZE sits below that with
room for tokenisation to vary by content — dense or non-English text packs more
tokens per character than the prose the measurement used.

Chunks overlap so a sentence spanning a boundary is still reachable from one
side or the other.
"""

from __future__ import annotations

# Measured content window of mxbai-embed-large, in characters. See module
# docstring. Re-measure if the embedding model changes.
MEASURED_WINDOW = 1604

# Deliberately below the measured window. The margin absorbs content that
# tokenises more densely than the prose used to measure.
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 120


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping windows no larger than chunk_size.

    Short text is returned as a single chunk so the common case adds no
    structure. Never returns an empty list for non-empty input.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    stride = chunk_size - overlap
    while start < len(text):
        chunks.append(text[start : start + chunk_size])
        start += stride
    return chunks


def chunk_record(record: dict, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """Expand one record into its embeddable chunks.

    Every chunk keeps its parent's identity and provenance so a retrieval hit
    can always be traced back to the record, the source path, and the source
    digest it came from. A chunk is a retrieval unit, never a separate work.
    """
    text = record.get("text", "")
    pieces = chunk_text(text, chunk_size, overlap)
    total = len(pieces)
    return [
        {
            "record_id": record.get("record_id"),
            "chunk_index": index,
            "chunk_count": total,
            "text": piece,
            "source_path": record.get("source_path"),
            "source_sha256": record.get("source_sha256"),
        }
        for index, piece in enumerate(pieces)
    ]
