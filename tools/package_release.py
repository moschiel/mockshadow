"""Build a portable ZIP from an already compiled extractor; never publishes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from distribution import VERSION, identity
from mockshadow_bootstrap import digest, platform_key


def run(*args):
    return subprocess.check_output([str(a) for a in args], text=True, errors='replace').strip()


def windows_runtime(executable, runtime, destination):
    objdump = runtime / 'objdump.exe'
    pending, seen = [executable], set()
    system = Path(os.environ['SystemRoot']) / 'System32'
    while pending:
        current = pending.pop()
        for name in re.findall(r'DLL Name:\s*(\S+)', run(objdump, '-p', current)):
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            source = runtime / name
            if source.is_file():
                shutil.copy2(source, destination / name)
                pending.append(source)
            elif not (system / name).is_file() and not name.lower().startswith(('api-ms-', 'ext-ms-')):
                raise ValueError(f'Unresolved runtime dependency: {name}')


def linux_runtime(executable, destination):
    # glibc and its loader remain part of the documented Ubuntu 24.04 baseline.
    for line in run('ldd', executable).splitlines():
        if 'not found' in line:
            raise ValueError(line)
        match = re.search(r'(\S+) => (/\S+)', line)
        if not match:
            continue
        name, path = match.groups()
        if name.startswith(('libc.so', 'libm.so', 'libpthread.so', 'libdl.so', 'librt.so')):
            continue
        shutil.copy2(Path(path).resolve(), destination / name)
    run('patchelf', '--force-rpath', '--set-rpath', '$ORIGIN', destination / executable.name)


def package(args):
    key = platform_key()
    extractor = ROOT / 'clang-code-extractor'
    executable = args.extractor or extractor / 'build' / ('extractor.exe' if os.name == 'nt' else 'extractor')
    executable = executable.resolve()
    if not executable.is_file():
        raise ValueError('Build the extractor before packaging')
    source = identity()
    source['extractor_commit'] = run('git', '-C', extractor, 'rev-parse', 'HEAD')
    source['extractor_dirty'] = bool(run('git', '-C', extractor, 'status', '--porcelain'))
    if (source['dirty'] or source['extractor_dirty']) and not args.allow_dirty:
        raise ValueError('Release packaging requires clean sources; use --allow-dirty only for local validation')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='package-', dir=output) as temporary:
        stage = Path(temporary)
        for path in ROOT.glob('*.py'):
            if path.name != 'setup.py':
                shutil.copy2(path, stage / path.name)
        shutil.copytree(ROOT / 'templates', stage / 'templates')
        # Public documentation and agent instructions travel with the runtime.
        for folder in ('docs', '.agents', '.claude'):
            shutil.copytree(ROOT / folder, stage / folder)
        for name in ('README.md', 'AGENTS.md', 'mockshadow.bat'):
            shutil.copy2(ROOT / name, stage / name)
        target = stage / 'clang-code-extractor'
        binary = target / 'build'
        binary.mkdir(parents=True)
        shutil.copy2(extractor / 'extract.py', target / 'extract.py')
        shutil.copy2(executable, binary / executable.name)
        resources = Path(run(args.clang, '-print-resource-dir'))
        shutil.copytree(resources / 'include', target / 'resources/include')
        if os.name == 'nt':
            windows_runtime(executable, args.runtime_bin, binary)
        else:
            linux_runtime(executable, binary)
        if not args.licenses.is_dir():
            raise ValueError('Supply --licenses with third-party redistribution notices')
        shutil.copytree(args.licenses, stage / 'THIRD-PARTY-NOTICES', symlinks=False)
        manifest = {'format': 1, 'version': VERSION, 'platform': key,
                    'baseline': 'Windows 10/11 x64' if os.name == 'nt' else 'Ubuntu 24.04 x64',
                    'python': '>=3.12', 'source': source,
                    'files': {p.relative_to(stage).as_posix(): digest(p)
                              for p in sorted(stage.rglob('*')) if p.is_file()}}
        (stage / 'distribution.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        name = f'mockshadow-{VERSION}-{key}.zip'
        archive = output / name
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            for path in sorted(stage.rglob('*')):
                if path.is_file():
                    info = zipfile.ZipInfo(path.relative_to(stage).as_posix(), (2026, 1, 1, 0, 0, 0))
                    info.external_attr = (0o100755 if path.stat().st_mode & 0o111 else 0o100644) << 16
                    z.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
        lock = {'version': VERSION, 'assets': {key: {
            'url': f'https://github.com/moschiel/mockshadow/releases/download/v{VERSION}/{name}',
            'sha256': digest(archive)}}}
        (output / f'lock-{key}.json').write_text(json.dumps(lock, indent=2) + '\n', encoding='utf-8')
        print(archive)
        print(f'SHA256: {digest(archive)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    parser.add_argument('--extractor', type=Path)
    parser.add_argument('--runtime-bin', type=Path, default=Path('C:/msys64/mingw64/bin'))
    parser.add_argument('--clang', default='clang')
    parser.add_argument('--licenses', type=Path, required=True)
    parser.add_argument('--allow-dirty', action='store_true')
    package(parser.parse_args())
