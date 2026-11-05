import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pipeline import generate, MANIFEST
from recipes import parse_recipe, relative_path
from audit import audit_project


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / 'firmware'
        self.project = self.root / 'simulator'
        self.original.mkdir()
        (self.project / '.mockshadow').mkdir(parents=True)
        self.tree = self.project / 'mocks'
        self.tree.mkdir()
        self.source = self.original / 'foo.c'
        self.source.write_text('int value = 1;\n')
        self.recipe = self.tree / 'arbitrary.c'
        self.config = {'formatVersion': 2, 'mocksDirectory': 'mocks'}
        self.write_recipe('int value = 2;\n')

    def write_recipe(self, body, target='foo.c', mode='replace', path=None):
        path = path or self.recipe
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f'//__MOCK_TARGET: {target}\n//__MOCK_MODE: {mode}\n'.encode() + body.encode('latin-1'))

    def run_generation(self, config=None, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return generate(self.project, self.original, {**self.config, **(config or {})}, **kwargs)

    def output(self):
        return (self.project / 'shadow_output/foo.c').read_text()

    def test_cache_rename_move_and_deleted_inputs(self):
        self.run_generation()
        with patch('pipeline.apply_recipe', side_effect=AssertionError('cache miss')):
            self.run_generation()
        self.write_recipe('int value = 3;\n')
        self.run_generation()
        before = self.output()
        moved = self.tree / 'completely/different.hpp'
        moved.parent.mkdir()
        self.recipe.rename(moved)
        self.run_generation()
        self.assertEqual(before, self.output())
        moved.unlink()
        self.run_generation()
        self.assertEqual(self.output(), self.source.read_text())
        self.source.unlink()
        self.run_generation()
        self.assertFalse((self.project / 'shadow_output/foo.c').exists())

    def test_retarget_restores_old_target(self):
        (self.original / 'other.c').write_text('other')
        self.run_generation()
        self.write_recipe('changed', target='other.c')
        self.run_generation()
        self.assertEqual(self.output(), self.source.read_text())
        self.assertEqual((self.project / 'shadow_output/other.c').read_text(), 'changed')

    def test_source_flags_corruption_force_and_old_manifest(self):
        first = self.run_generation()
        self.source.write_text('new source')
        os.utime(self.source, (1, 1))
        second = self.run_generation()
        self.assertNotEqual(first['context'], second['context'])
        third = self.run_generation({'extractorCFlags': ['-DNEW']})
        self.assertNotEqual(second['context'], third['context'])
        (self.project / 'shadow_output/foo.c').write_text('corrupt')
        self.run_generation()
        self.assertEqual(self.output(), 'int value = 2;\n')
        self.run_generation(force=True)
        manifest = self.project / 'shadow_output' / MANIFEST
        data=json.loads(manifest.read_text()); data['version']=1
        manifest.write_text(json.dumps(data))
        with patch('pipeline.apply_recipe', wraps=__import__('recipes').apply_recipe) as transform:
            self.run_generation()
            self.assertEqual(transform.call_count, 1)

    def test_failure_preserves_output_and_source(self):
        self.run_generation()
        output = self.project / 'shadow_output'
        before = {p.name:p.read_bytes() for p in output.iterdir()}
        self.write_recipe('//__MOCK_REPLACE_TEXT_LINE: absent\nreplacement\n', mode='patch')
        with self.assertRaises(SystemExit): self.run_generation()
        self.assertEqual(before, {p.name:p.read_bytes() for p in output.iterdir()})
        self.assertEqual(self.source.read_text(), 'int value = 1;\n')
        self.assertFalse((self.project / '.mockshadow/generation.lock').exists())

    def test_publish_rollback_recovery_and_lock(self):
        self.run_generation()
        output=self.project/'shadow_output'
        before=(output/MANIFEST).read_bytes()
        rename=Path.rename
        def fail(path,target):
            if path.name=='tree': raise PermissionError('simulated failure')
            return rename(path,target)
        self.write_recipe('changed')
        with patch.object(Path,'rename',fail):
            with self.assertRaises(PermissionError): self.run_generation()
        self.assertEqual(before,(output/MANIFEST).read_bytes())
        output.rename(self.project/'.mockshadow/previous-tree')
        self.run_generation()
        self.assertEqual(self.output(),'changed')
        (self.project/'.mockshadow/generation.lock').write_text('busy')
        with self.assertRaises(RuntimeError): self.run_generation()

    def test_old_dates_refresh_only_changed_output(self):
        self.recipe.unlink(); self.run_generation()
        target=self.project/'shadow_output/foo.c'
        stamp=target.stat().st_mtime_ns
        self.run_generation(); self.assertEqual(stamp,target.stat().st_mtime_ns)
        os.utime(target,(1000,1000)); self.source.write_text('changed'); os.utime(self.source,(1,1))
        self.run_generation(); self.assertGreater(target.stat().st_mtime,1000)

    def test_additions_duplicates_exclusions_and_dependency_collision(self):
        (self.project/'support').mkdir()
        (self.project/'support/device.hpp').write_text('#pragma once\n')
        item={'source':'support/device.hpp','destination':'host/device.hpp'}
        self.run_generation({'additionalFiles':[item]})
        self.assertTrue((self.project/'shadow_output/host/device.hpp').is_file())
        self.run_generation()
        self.assertFalse((self.project/'shadow_output/host/device.hpp').exists())
        for config in ({'additionalFiles':[item,item]}, {'additionalFiles':[{**item,'destination':'foo.c'}]},
                       {'additionalFiles':[{**item,'destination':'foo.c/nested.h'}]},
                       {'excludeFromCopy':['foo.c']}, {'addToCopy':[{'src':'support','temp_dest':'foo.c'}]}):
            with self.subTest(config=config), self.assertRaises(ValueError): self.run_generation(config)
        self.write_recipe('duplicate',path=self.tree/'duplicate.c')
        with self.assertRaisesRegex(ValueError,'Duplicate'): self.run_generation()

    def test_replace_bytes_and_metadata_validation(self):
        self.write_recipe('/* a\xe7\xe3o */\r\nint x;\r\n')
        self.run_generation()
        self.assertEqual((self.project/'shadow_output/foo.c').read_bytes(), b'/* a\xe7\xe3o */\r\nint x;\r\n')
        for bad in ('legacy', '//__MOCK_TARGET: foo.c\n', '//__MOCK_TARGET: ../foo.c\n//__MOCK_MODE: patch\n',
                    '//__MOCK_TARGET: foo.c\n//__MOCK_MODE: invalid\n',
                    '//__MOCK_TARGET: foo.c\n//__MOCK_MODE: patch\nint x;\n//__MOCK_MODE: patch\n'):
            self.recipe.write_text(bad)
            with self.subTest(bad=bad), self.assertRaises(ValueError): self.run_generation()
        for bad in ('../foo.c', '/foo.c', 'C:/foo.c', 'C:foo.c', 'a\\b.c', './foo.c'):
            with self.subTest(path=bad), self.assertRaises(ValueError): relative_path(bad)
        with self.assertRaises(ValueError): generate(self.project,self.original,{})
        with self.assertRaises(ValueError): generate(self.project,self.project,self.config)

    def test_audit_continues_and_preserves_all_inputs_and_outputs(self):
        (self.original/'bar.hpp').write_text('#ifndef BAR\n#define BAR\n#endif\n')
        self.write_recipe('//__MOCK_BOTTOM_START\nint added;\n//__MOCK_BOTTOM_END\n',target='bar.hpp',mode='patch',path=self.tree/'header.cpp')
        self.run_generation()
        self.write_recipe('//__MOCK_REPLACE_TEXT_LINE: absent\nx\n',mode='patch')
        before={p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with contextlib.redirect_stdout(io.StringIO()): report=audit_project(self.project,self.original,self.config)
        self.assertEqual((report['files'],report['passed'],report['failed']),(2,1,1))
        self.assertEqual(before,{p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_cli_contract_and_open_mock(self):
        from open_mock import open_mock
        self.assertEqual(open_mock(self.project,self.original,self.config,'foo.c'),self.recipe)
        (self.original/'new.cpp').write_text('int x;')
        created=open_mock(self.project,self.original,self.config,'new.cpp','feature/custom.cpp')
        self.assertEqual(parse_recipe(created).target,'new.cpp')
        tool=Path(__file__).resolve().parents[1]/'mockshadow.py'
        for args in (['--help'],['--version'],['mock','--help']):
            self.assertEqual(subprocess.run([sys.executable,str(tool),*args],cwd=self.root,capture_output=True).returncode,0)
        for args in (['version'],['mock','details'],['remock'],['unmock'],['clone-tree'],['mock','--det']):
            self.assertEqual(subprocess.run([sys.executable,str(tool),*args],cwd=self.root,capture_output=True).returncode,2)
        result=subprocess.run([sys.executable,str(tool),'create-project','created'],cwd=self.root,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((self.root/'created/mocks').is_dir())


if __name__ == '__main__': unittest.main()
