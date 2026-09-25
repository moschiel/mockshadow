import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit import audit_project


class AuditTests(unittest.TestCase):
    def test_reports_drift_continues_and_preserves_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original, mocks = root / "original", root / "MOCK_TREE"
            original.mkdir()
            mocks.mkdir()
            (original / "a.c").write_text("int old_value = 1;\n")
            (original / "b.c").write_text("int good_value = 2;\n")
            (original / "d.h").write_text("#define MCU 1\n")
            (mocks / "__mock__a.c").write_text(
                "//__MOCK_COPY_FILE_CONTENT__\n//__MOCK_REPLACE_TEXT_LINE: absent\nreplacement\n")
            (mocks / "__mock__b.c").write_text(
                "//__MOCK_COPY_FILE_CONTENT__\n//__MOCK_REPLACE_TEXT_LINE: good_value\nnew_value\n")
            (mocks / "__mock__c.c").write_text("int missing_source;\n")
            (mocks / "__mock__d.h").write_text("#define MCU 2\n")
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            with contextlib.redirect_stdout(io.StringIO()):
                result = audit_project(original, mocks)
            self.assertEqual((result["files"], result["passed"], result["failed"]), (4, 2, 2))
            self.assertEqual([r["status"] for r in result["results"]],
                             ["transform_failed", "ok", "missing_source", "ok"])
            self.assertIn("absent", result["results"][0]["diagnostic"])
            after = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
