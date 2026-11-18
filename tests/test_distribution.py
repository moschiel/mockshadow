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
        self.root = Path(self.tmp.name)
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
        self.env = patch.dict('os.environ', {'MOCKSHADOW_ROOT': ''})
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
        self.assertEqual(list((self.project / '.tools').iterdir()), [])

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
        self.assertEqual(list((self.project / '.tools').iterdir()), [])

    def test_check_does_not_create_directories(self):
        with self.assertRaisesRegex(ValueError, 'missing'):
            b.resolve(self.project, install=False)
        self.assertFalse((self.project / '.tools').exists())

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
