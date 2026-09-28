import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pipeline import generate, MANIFEST


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / "firmware"
        self.project = self.root / "simulator"
        self.original.mkdir()
        (self.project / ".mockshadow").mkdir(parents=True)
        self.tree = self.project / "MOCK_TREE"
        self.tree.mkdir()
        self.source = self.original / "foo.c"
        self.source.write_text("int value = 1;\n")
        self.recipe = self.tree / "__mock__foo.c"
        self.recipe.write_text("int value = 2;\n")

    def run_generation(self, config=None, **kwargs):
        return generate(self.project, self.original, config or {}, **kwargs)

    def test_content_cache_and_deleted_inputs(self):
        first = self.run_generation()
        with patch("pipeline.mock_utils.check_file_mock_mode", side_effect=AssertionError("cache miss")):
            self.run_generation()
        stamp = self.recipe.stat().st_mtime
        self.recipe.write_text("int value = 3;\n")
        os.utime(self.recipe, (stamp, stamp))
        second = self.run_generation()
        self.assertNotEqual(first["recipes"], second["recipes"])
        self.assertEqual((self.project / "shadow_output/foo.c").read_text(), "int value = 3;\n")
        (self.tree / "foo.c").write_text("stale legacy output")
        self.recipe.unlink()
        self.run_generation()
        self.assertEqual((self.project / "shadow_output/foo.c").read_text(), self.source.read_text())
        self.source.unlink()
        self.run_generation()
        self.assertFalse((self.project / "shadow_output/foo.c").exists())

    def test_source_flags_and_output_corruption_invalidate(self):
        first = self.run_generation()
        self.source.write_text("int value = 4;\n")
        os.utime(self.source, (1, 1))
        second = self.run_generation()
        self.assertNotEqual(first["context"], second["context"])
        third = self.run_generation({"extractorCFlags": ["-DNEW_BRANCH"]})
        self.assertNotEqual(second["context"], third["context"])
        (self.project / "shadow_output/foo.c").write_text("corrupt")
        self.run_generation()
        self.assertEqual((self.project / "shadow_output/foo.c").read_text(), self.recipe.read_text())

    def test_failure_preserves_complete_output_and_manifest(self):
        self.run_generation()
        output = self.project / "shadow_output"
        before = {p.name: p.read_bytes() for p in output.iterdir()}
        self.recipe.write_text("//__MOCK_COPY_FILE_CONTENT__\n//__MOCK_REPLACE_TEXT_LINE: absent\nreplacement\n")
        with self.assertRaises(SystemExit):
            self.run_generation()
        self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})
        self.assertEqual(self.source.read_text(), "int value = 1;\n")
        self.assertFalse((self.project / ".mockshadow/generation.lock").exists())

    def test_exclusions_additions_and_traversal(self):
        (self.original / "excluded").mkdir()
        (self.original / "excluded/secret.c").write_text("secret")
        (self.tree / "__additional__device.h").write_text("model")
        self.run_generation({"excludeFromCopy": ["excluded"]})
        self.assertFalse((self.project / "shadow_output/excluded").exists())
        self.assertTrue((self.project / "shadow_output/__additional__device.h").exists())
        with self.assertRaises(ValueError):
            self.run_generation({"addToCopy": [{"src": ".", "temp_dest": "../escape"}]})
        with self.assertRaises(ValueError):
            generate(self.project, self.project, {})

    def test_publish_failure_rolls_back_and_interrupted_rename_recovers(self):
        self.run_generation()
        output = self.project / "shadow_output"
        before = (output / MANIFEST).read_bytes()
        rename = Path.rename
        def fail_publish(path, target):
            if path.name == "tree":
                raise PermissionError("simulated Windows sharing violation")
            return rename(path, target)
        self.recipe.write_text("int new_value = 8;\n")
        with patch.object(Path, "rename", fail_publish):
            with self.assertRaises(PermissionError):
                self.run_generation()
        self.assertEqual(before, (output / MANIFEST).read_bytes())
        output.rename(self.project / ".mockshadow/previous-tree")
        self.run_generation()
        self.assertEqual((output / "foo.c").read_text(), self.recipe.read_text())

    def test_lock_rejects_second_generator(self):
        lock = self.project / ".mockshadow/generation.lock"
        lock.write_text("another process")
        with self.assertRaises(RuntimeError):
            self.run_generation()
        self.assertEqual(lock.read_text(), "another process")

    def test_old_branch_dates_cannot_leave_stale_compiler_objects(self):
        self.recipe.unlink()
        self.run_generation()
        target = self.project / "shadow_output/foo.c"
        first_date = target.stat().st_mtime_ns
        self.run_generation()
        self.assertEqual(first_date, target.stat().st_mtime_ns)
        os.utime(target, (1000, 1000))
        self.source.write_text("int branch_value = 99;\n")
        os.utime(self.source, (1, 1))
        self.run_generation()
        self.assertGreater(target.stat().st_mtime, 1000)
        self.assertEqual(target.read_text(), self.source.read_text())


if __name__ == "__main__":
    unittest.main()
