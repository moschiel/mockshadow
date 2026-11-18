import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SPEC = importlib.util.spec_from_file_location('bootstrap', Path(__file__).resolve().parents[1] / 'tools/mockshadow_bootstrap.py')
b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(b)


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.project = self.root / 'consumer'
        self.project.mkdir()
        self.package = self.root / 'tool.zip'
        import os
        files = {'mockshadow.py': 'print("fixture")', 'distribution.py': '',
                 'clang-code-extractor/extract.py': 'print("1;1")',
                 'clang-code-extractor/build/' + ('extractor.exe' if os.name == 'nt' else 'extractor'): 'fixture'}
        import hashlib
        manifest = {'version': '2.1.0', 'platform': b.platform_key(),
                    'files': {n: hashlib.sha256(v.encode()).hexdigest() for n, v in files.items()}}
        with zipfile.ZipFile(self.package, 'w') as z:
            for name, text in files.items():
                z.writestr(name, text)
            z.writestr('distribution.json', json.dumps(manifest))
        self.lock = {'version': '2.1.0', 'assets': {b.platform_key(): {
            'url': 'https://example.invalid/tool.zip', 'sha256': b.digest(self.package)}}}
        self.save_lock()
        self.env = patch.dict('os.environ', {'MOCKSHADOW_ROOT': '', 'MOCKSHADOW_HOME': str(self.root / 'shared')})
        self.env.start()
        self.addCleanup(self.env.stop)

    def save_lock(self):
        (self.project / 'mockshadow.lock.json').write_text(json.dumps(self.lock))

    def test_offline_install_reuse_and_tamper(self):
        root = b.resolve(self.project, archive=self.package)
        with patch.object(b.urllib.request, 'urlopen', side_effect=AssertionError('network')):
            self.assertEqual(root, b.resolve(self.project, install=False))
        (root / 'mockshadow.py').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            b.resolve(self.project)

    def test_bad_hash_never_installs(self):
        self.lock['assets'][b.platform_key()]['sha256'] = '0' * 64
        self.save_lock()
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            b.resolve(self.project, archive=self.package)
        self.assertEqual(list((self.root / 'shared/packages').iterdir()), [])

    def test_download_then_reuse_without_network(self):
        import io
        response = io.BytesIO(self.package.read_bytes())
        response.geturl = lambda: 'https://example.invalid/tool.zip'
        with patch.object(b.urllib.request, 'urlopen', return_value=response) as download:
            root = b.resolve(self.project)
            download.assert_called_once_with('https://example.invalid/tool.zip', timeout=60)
        with patch.object(b.urllib.request, 'urlopen', side_effect=AssertionError('network')):
            self.assertEqual(b.resolve(self.project), root)

    def test_download_failure_releases_install_lock(self):
        with patch.object(b.urllib.request, 'urlopen', side_effect=OSError('offline')):
            with self.assertRaisesRegex(OSError, 'offline'):
                b.resolve(self.project)
        self.assertEqual(list((self.root / 'shared/packages').iterdir()), [])

    def test_check_does_not_create_directories(self):
        with self.assertRaisesRegex(ValueError, 'missing'):
            b.resolve(self.project, install=False)
        self.assertFalse((self.root / 'shared/packages').exists())

    def test_publish_retries_transient_windows_handle(self):
        from unittest.mock import Mock
        stage = Mock()
        error = OSError('temporary loader handle')
        error.winerror = 5
        stage.rename.side_effect = [error, None]
        with patch.object(b.time, 'sleep'):
            b.publish(stage, self.root / 'installed')
        self.assertEqual(stage.rename.call_count, 2)

    def test_explicit_override_without_lock_or_network(self):
        (self.project / 'mockshadow.lock.json').unlink()
        local = self.root / 'dev'
        local.mkdir()
        (local / 'mockshadow.py').touch()
        self.assertEqual(b.resolve(self.project, '../dev'), local)
        with self.assertRaisesRegex(ValueError, 'Invalid MOCKSHADOW_ROOT'):
            b.resolve(self.project, '../missing')

    def test_two_projects_share_one_download(self):
        import io
        second = self.root / 'second'
        second.mkdir()
        (second / 'mockshadow.lock.json').write_text(json.dumps(self.lock))
        response = io.BytesIO(self.package.read_bytes())
        response.geturl = lambda: 'https://example.invalid/tool.zip'
        with patch.object(b.urllib.request, 'urlopen', return_value=response) as download:
            first = b.resolve(self.project)
            self.assertEqual(first, b.resolve(second))
            self.assertEqual(download.call_count, 1)
        self.assertFalse((second / '.tools').exists())

    def test_concurrent_projects_share_installation(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: b.resolve(self.project, archive=self.package), range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(len(list((self.root / 'shared/packages').iterdir())), 1)

    def test_command_selects_nearest_project(self):
        child = self.project / 'nested'
        child.mkdir()
        self.assertEqual(b.command_project(child), self.project)
        with self.assertRaisesRegex(ValueError, 'No mockshadow.lock'):
            b.command_project(self.root)

    def test_migration_reuses_package_and_cleans_local_copies(self):
        import shutil
        import sys
        installed = b.resolve(self.project, archive=self.package)
        second = self.root / 'second'
        second.mkdir()
        (second / 'mockshadow.lock.json').write_text(json.dumps(self.lock))
        for project in (self.project, second):
            (project / '.tools').mkdir()
            shutil.copytree(installed, project / '.tools' / installed.name)
        shutil.rmtree(installed)
        spec = importlib.util.spec_from_file_location('migration', Path(b.__file__).with_name('migrate_shared.py'))
        migration = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'mockshadow_bootstrap': b}):
            spec.loader.exec_module(migration)
        argv = ['migrate', '--project', str(self.project), '--project', str(second)]
        with patch.object(sys, 'argv', argv), patch.object(migration, 'install_command'), patch.object(b.urllib.request, 'urlopen', side_effect=AssertionError('network')):
            migration.main()
        self.assertEqual(b.resolve(self.project), b.resolve(second))
        self.assertFalse((self.project / '.tools').exists())
        self.assertFalse((second / '.tools').exists())

    def test_traversal_and_links(self):
        with self.assertRaises(ValueError):
            b.safe_name('a\\b')  # ZipFile normalizes this on Windows when writing.
        for name in ('../escape', '/absolute', 'C:/escape', 'x/../y'):
            with self.subTest(name=name):
                with zipfile.ZipFile(self.package, 'w') as z:
                    z.writestr(name, 'bad')
                with self.assertRaises(ValueError):
                    b.extract(self.package, self.root / 'out')
        with zipfile.ZipFile(self.package, 'w') as z:
            item = zipfile.ZipInfo('link')
            item.external_attr = 0o120777 << 16
            z.writestr(item, '../escape')
        with self.assertRaisesRegex(ValueError, 'Links'):
            b.extract(self.package, self.root / 'out')


if __name__ == '__main__':
    unittest.main()
