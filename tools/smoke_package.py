"""Exercise a portable package without Git, LLVM or MSYS2 on PATH."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from mockshadow_bootstrap import resolve, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('lock', type=Path)
    args = parser.parse_args()
    os.environ.pop('MOCKSHADOW_ROOT', None)
    with tempfile.TemporaryDirectory(prefix='mockshadow-smoke-') as temporary:
        root = Path(temporary)
        os.environ['MOCKSHADOW_HOME'] = str(root / 'shared')
        shutil.copy2(args.lock, root / 'mockshadow.lock.json')
        tool = resolve(root, archive=args.archive)
        env = dict(os.environ, PATH=os.path.join(os.environ.get('SystemRoot', '/usr'), 'System32')
                   if os.name == 'nt' else '/usr/bin:/bin', PYTHONDONTWRITEBYTECODE='1')
        # Include a Clang builtin header to exercise packaged resource lookup.
        source = root / 'source with spaces.c'
        source.write_text('#include <stdint.h>\nint answer(void) { return 42; }\n')
        def extract(index):
            result = subprocess.run([sys.executable, '-B', str(tool / 'clang-code-extractor/extract.py'),
                'function', 'answer', str(source), 'lines'], env=env, cwd=root,
                capture_output=True, text=True, check=True)
            assert result.stdout.strip() == '2;2', result.stdout + result.stderr
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(extract, range(8)))
        firmware, simulator = root / 'firmware', root / 'simulator'
        firmware.mkdir()
        (firmware / 'main.c').write_text('int answer(void) { return 1; }\n')
        (simulator / '.mockshadow').mkdir(parents=True)
        (simulator / 'mocks').mkdir()
        (simulator / '.mockshadow/env.json').write_text(json.dumps({'originalProject': str(firmware)}))
        (simulator / '.mockshadow/config.json').write_text(json.dumps({
            'formatVersion': 2, 'mocksDirectory': 'mocks', 'additionalFiles': []}))
        (simulator / 'mocks/answer.c').write_text('//__MOCK_TARGET: main.c\n//__MOCK_MODE: patch\n'
            '//__MOCK_REPLACE_CODE_START: function answer\nint answer(void) { return 42; }\n//__MOCK_REPLACE_CODE_END\n')
        for command in ('mock', 'audit', 'mock'):
            subprocess.run([sys.executable, '-B', str(tool / 'mockshadow.py'), command], cwd=simulator, env=env, check=True)
        assert 'return 42;' in (simulator / 'shadow_output/main.c').read_text()
        assert 'return 1;' in (firmware / 'main.c').read_text()
        verify(tool, json.loads(args.lock.read_text())['version'])
        assert not (root / 'definition.txt').exists()
        print('PASS: offline installation, concurrent extraction, mock/audit/cache, immutable tool and source')


if __name__ == '__main__':
    main()
