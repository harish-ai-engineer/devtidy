import os
import tempfile
import time
import unittest
from pathlib import Path

from devtidy.scanner import scan


class ScannerTests(unittest.TestCase):
    def test_node_modules_requires_package_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "app"
            modules = project / "node_modules"
            modules.mkdir(parents=True)
            (modules / "dependency.js").write_text("x" * 100, encoding="utf-8")

            self.assertEqual(scan([root]), [])
            (project / "package.json").write_text("{}", encoding="utf-8")
            candidates = scan([root])

            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].rule, "node_modules")

    def test_virtualenv_requires_pyvenv_cfg(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = root / "project" / ".venv"
            environment.mkdir(parents=True)
            self.assertEqual(scan([root]), [])

            (environment / "pyvenv.cfg").write_text("home = python", encoding="utf-8")
            self.assertEqual(scan([root])[0].rule, "python_venv")

    def test_age_filter_uses_project_activity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "app"
            modules = project / "node_modules"
            modules.mkdir(parents=True)
            package = project / "package.json"
            package.write_text("{}", encoding="utf-8")
            old = time.time() - 10 * 86400
            os.utime(modules, (old, old))
            os.utime(package, (old, old))

            self.assertEqual(len(scan([root], older_than_seconds=5 * 86400)), 1)
            package.touch()
            self.assertEqual(scan([root], older_than_seconds=5 * 86400), [])

    def test_matched_parent_suppresses_nested_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = root / "project" / ".venv"
            cache = environment / "lib" / "__pycache__"
            cache.mkdir(parents=True)
            (environment / "pyvenv.cfg").write_text("home = python", encoding="utf-8")

            candidates = scan([root])
            self.assertEqual([item.rule for item in candidates], ["python_venv"])


if __name__ == "__main__":
    unittest.main()

