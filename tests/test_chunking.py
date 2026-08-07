from __future__ import annotations

import unittest

from lore.chunking import CHUNK_OVERLAP, CHUNK_SIZE, MEASURED_WINDOW, chunk_record, chunk_text


class ChunkTextTests(unittest.TestCase):
    """The property that matters: no chunk can exceed the model's window.

    A chunk larger than the window is embedded from its opening only, and the
    model reports no error — so the failure is invisible at build time and
    shows up as a package that retrieves badly for reasons nobody can see.
    """

    def test_default_chunk_size_is_below_the_measured_window(self) -> None:
        self.assertLess(CHUNK_SIZE, MEASURED_WINDOW)

    def test_short_text_is_one_chunk(self) -> None:
        self.assertEqual(chunk_text("brief"), ["brief"])

    def test_no_chunk_exceeds_chunk_size(self) -> None:
        text = "x" * (CHUNK_SIZE * 7 + 13)
        for chunk in chunk_text(text):
            self.assertLessEqual(len(chunk), CHUNK_SIZE)

    def test_every_character_is_covered(self) -> None:
        text = "".join(chr(97 + i % 26) for i in range(CHUNK_SIZE * 4))
        chunks = chunk_text(text)
        # Reassembling by stride must reproduce the original exactly.
        stride = CHUNK_SIZE - CHUNK_OVERLAP
        rebuilt = "".join(chunk[:stride] for chunk in chunks)
        self.assertEqual(rebuilt[: len(text)], text)

    def test_chunks_overlap_so_boundaries_stay_reachable(self) -> None:
        text = "y" * (CHUNK_SIZE * 2)
        chunks = chunk_text(text)
        self.assertGreater(len(chunks), 1)
        tail = chunks[0][-CHUNK_OVERLAP:]
        self.assertTrue(chunks[1].startswith(tail))

    def test_empty_text_yields_one_empty_chunk(self) -> None:
        self.assertEqual(chunk_text(""), [""])

    def test_rejects_overlap_at_or_above_chunk_size(self) -> None:
        with self.assertRaises(ValueError):
            chunk_text("text", chunk_size=100, overlap=100)

    def test_rejects_non_positive_chunk_size(self) -> None:
        with self.assertRaises(ValueError):
            chunk_text("text", chunk_size=0)


class ChunkRecordTests(unittest.TestCase):
    def test_provenance_survives_on_every_chunk(self) -> None:
        record = {
            "record_id": "abc123",
            "text": "z" * (CHUNK_SIZE * 3),
            "source_path": "raw/z80/manual.txt",
            "source_sha256": "deadbeef",
        }
        chunks = chunk_record(record)
        self.assertGreater(len(chunks), 1)
        for index, chunk in enumerate(chunks):
            self.assertEqual(chunk["record_id"], "abc123")
            self.assertEqual(chunk["source_path"], "raw/z80/manual.txt")
            self.assertEqual(chunk["source_sha256"], "deadbeef")
            self.assertEqual(chunk["chunk_index"], index)
            self.assertEqual(chunk["chunk_count"], len(chunks))

    def test_a_short_record_still_produces_one_traceable_chunk(self) -> None:
        chunks = chunk_record({"record_id": "solo", "text": "short", "source_path": "p", "source_sha256": "d"})
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["chunk_index"], 0)
        self.assertEqual(chunks[0]["chunk_count"], 1)

    def test_the_regression_this_exists_to_prevent(self) -> None:
        """Two documents sharing an opening must not collapse to one unit.

        In org.magesguild.z80-computing 1.0.0 three unrelated disk images of
        67.8MB, 17.0MB and 8.5MB shared a byte-identical vector because each
        was embedded whole and the model read only the opening. Chunked, the
        differing tails occupy their own chunks and remain distinguishable.
        """
        shared = "s" * (CHUNK_SIZE * 2)
        first = chunk_record({"record_id": "a", "text": shared + "TAIL-ONE"})
        second = chunk_record({"record_id": "b", "text": shared + "TAIL-TWO"})
        self.assertNotEqual(
            [c["text"] for c in first],
            [c["text"] for c in second],
        )


if __name__ == "__main__":
    unittest.main()
