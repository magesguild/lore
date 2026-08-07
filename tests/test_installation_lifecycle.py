from __future__ import annotations

import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

from lore.cli import activate_package, history_package, install_package, rollback_package, verify_package


def _package(root: Path, version: str, *, text: str = "knowledge") -> Path:
    package = root / f"package-{version}"
    package.mkdir(parents=True)
    (package / "records.jsonl").write_text(
        json.dumps({"record_id": "r1", "text": text, "knowledge_status": "curated"}) + "\n",
        encoding="utf-8",
    )
    (package / "embeddings.f32").write_bytes(struct.pack("<2f", 1.0, 0.0))
    (package / "embedding_index.jsonl").write_text(
        json.dumps({"record_id": "r1", "row": 0, "chars": len(text)}) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema": "lore-package-v1",
        "package_id": "org.test.knowledge",
        "version": version,
        "records": 1,
        "knowledge_not_memory": True,
        "embedding": {"model": "test", "dimensions": 2, "dtype": "float32", "endianness": "little"},
        "artifacts": {"records": "records.jsonl", "embeddings": "embeddings.f32", "embedding_index": "embedding_index.jsonl"},
    }
    manifest["artifact_digests"] = {
        name: hashlib.sha256((package / name).read_bytes()).hexdigest()
        for name in ("records.jsonl", "embeddings.f32", "embedding_index.jsonl")
    }
    (package / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return package


class InstallationLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.install_root = self.root / "collections"

    def test_install_is_staged_without_activation_by_default(self) -> None:
        package = _package(self.root, "1.0.0")
        self.assertEqual(install_package(package, self.install_root), 0)
        package_root = self.install_root / "org.test.knowledge"
        self.assertFalse((package_root / "active").exists())
        self.assertTrue((package_root / "versions" / "1.0.0" / "package" / "manifest.json").is_file())
        events = (package_root / "history.jsonl").read_text().splitlines()
        self.assertEqual(json.loads(events[0])["event"], "install")

    def test_activation_and_rollback_move_only_the_pointer(self) -> None:
        old = _package(self.root, "1.0.0", text="old")
        new = _package(self.root, "1.0.1", text="new")
        install_package(old, self.install_root)
        install_package(new, self.install_root)
        activate_package("org.test.knowledge", "1.0.0", self.install_root)
        activate_package("org.test.knowledge", "1.0.1", self.install_root)
        package_root = self.install_root / "org.test.knowledge"
        self.assertEqual((package_root / "active").resolve().name, "1.0.1")
        rollback_package("org.test.knowledge", "1.0.0", self.install_root)
        self.assertEqual((package_root / "active").resolve().name, "1.0.0")
        self.assertTrue((package_root / "versions" / "1.0.1" / "package" / "records.jsonl").is_file())

    def test_same_version_different_bytes_is_refused(self) -> None:
        first = _package(self.root, "1.0.0", text="first")
        second = _package(self.root / "other", "1.0.0", text="second")
        install_package(first, self.install_root)
        with self.assertRaises(SystemExit):
            install_package(second, self.install_root)

    def test_same_version_same_bytes_is_idempotent(self) -> None:
        first = _package(self.root, "1.0.0")
        second = _package(self.root / "other", "1.0.0")
        install_package(first, self.install_root)
        self.assertEqual(install_package(second, self.install_root), 0)

    def test_history_is_readable(self) -> None:
        package = _package(self.root, "1.0.0")
        install_package(package, self.install_root)
        self.assertEqual(history_package("org.test.knowledge", self.install_root), 0)

    def test_verify_refuses_artifact_path_escape(self) -> None:
        package = _package(self.root, "1.0.0")
        manifest = json.loads((package / "manifest.json").read_text())
        manifest["artifacts"]["records"] = "../outside.jsonl"
        (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(SystemExit):
            verify_package(package)
