import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from devtidy.scanner import scan
from devtidy.storage import archive, restore


class ArchiveTests(unittest.TestCase):
    def test_archive_and_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "projects"
            modules = root / "app" / "node_modules"
            modules.mkdir(parents=True)
            (root / "app" / "package.json").write_text("{}", encoding="utf-8")
            (modules / "file.js").write_text("content", encoding="utf-8")

            with patch("devtidy.storage.state_dir", return_value=base / "state"):
                candidates = scan([root])
                manifest = archive(candidates)
                self.assertFalse(modules.exists())

                restored = restore(manifest["session_id"], latest=False, overwrite=False)
                self.assertEqual(len(restored["items"]), 1)
                self.assertTrue((modules / "file.js").is_file())

    def test_restore_rejects_path_outside_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            session = base / "state" / "archives" / "bad-session"
            session.mkdir(parents=True)
            manifest = {
                "session_id": "bad-session",
                "total_size": 1,
                "items": [
                    {
                        "archived_path": str(base / "outside"),
                        "path": str(base / "projects" / "node_modules"),
                        "root": str(base / "projects"),
                    }
                ],
            }
            (session / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            with patch("devtidy.storage.state_dir", return_value=base / "state"):
                with self.assertRaisesRegex(ValueError, "invalid archived path"):
                    restore("bad-session", latest=False, overwrite=False)


if __name__ == "__main__":
    unittest.main()
