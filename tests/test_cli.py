import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from devtidy.cli import main
from devtidy.models import Candidate
from devtidy.ui import make_console, render_candidates


class CliTests(unittest.TestCase):
    def test_json_output_has_no_terminal_markup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache = root / "__pycache__"
            cache.mkdir()
            (cache / "module.pyc").write_bytes(b"cache")
            output = StringIO()

            with redirect_stdout(output):
                exit_code = main(["scan", str(root), "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload[0]["category"], "cache")

    def test_no_color_candidate_output(self):
        output = StringIO()
        console = make_console(no_color=True)
        console.file = output
        candidate = Candidate(
            path=Path("project/node_modules"),
            root=Path("project"),
            rule="node_modules",
            category="node",
            size=1024,
            last_activity=0,
        )

        render_candidates(console, [candidate])

        rendered = output.getvalue()
        self.assertIn("Potential savings", rendered)
        self.assertNotIn("\x1b[", rendered)


if __name__ == "__main__":
    unittest.main()
