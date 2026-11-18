"""Vendored stdlib-only installer. Canonical source: Mockshadow tools/.

Python 3.12+. No global PATH changes, source builds or implicit latest version.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
import zipfile


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def platform_key():
    machine = platform.machine().lower()
    if machine not in ('amd64', 'x86_64'):
        raise ValueError(f'No prebuilt Mockshadow for {machine}; set MOCKSHADOW_ROOT to a built checkout.')
    return {'win32': 'windows-x64', 'linux': 'linux-x64'}.get(sys.platform, sys.platform + '-x64')


def safe_name(name):
    path = PurePosixPath(name)
    if (not name or '\\' in name or ':' in name or path.is_absolute()
            or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError(f'Unsafe package path: {name}')
    return path


def verify(root, version):
    manifest = json.loads((root / 'distribution.json').read_text(encoding='utf-8'))
    if manifest['version'] != version or manifest['platform'] != platform_key():
        raise ValueError('Mockshadow distribution version/platform mismatch')
    files = manifest['files']
    for name, expected in files.items():
        file = root.joinpath(*safe_name(name).parts)
        if file.is_symlink() or file.is_junction() or not file.is_file() or digest(file) != expected:
            raise ValueError(f'Mockshadow package changed or incomplete: {name}')
    actual = set()
    for file in root.rglob('*'):
        if file.is_symlink() or file.is_junction():
            raise ValueError(f'Linked package path: {file}')
        if file.is_file():
            actual.add(file.relative_to(root).as_posix())
    if actual != set(files) | {'distribution.json'}:
        raise ValueError('Unexpected files in Mockshadow installation')
    executable = 'extractor.exe' if os.name == 'nt' else 'extractor'
    for required in ('mockshadow.py', 'distribution.py', 'clang-code-extractor/extract.py',
                     'clang-code-extractor/build/' + executable):
        if required not in files:
            raise ValueError(f'Package missing {required}')
    return manifest


def extract(archive, destination):
    seen = set()
    with zipfile.ZipFile(archive) as package:
        for item in package.infolist():
            name = item.filename.rstrip('/') if item.is_dir() else item.filename
            rel = safe_name(name)
            if name.casefold() in seen:
                raise ValueError(f'Duplicate archive path: {name}')
            seen.add(name.casefold())
            mode = item.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError('Links are not allowed in distributions')
            target = destination.joinpath(*rel.parts)
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with package.open(item) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output)
            target.chmod(0o755 if mode & 0o111 else 0o644)


def resolve(project, override=None, *, install=True, archive=None):
    if sys.version_info < (3, 12):
        raise ValueError('Mockshadow requires Python 3.12+')
    project = Path(project).resolve()
    override = override or os.environ.get('MOCKSHADOW_ROOT', '').strip()
    if override:
        root = (project / override).resolve()
        if not (root / 'mockshadow.py').is_file():
            raise ValueError(f'Invalid MOCKSHADOW_ROOT: {root}')
        return root
    lock = json.loads((project / 'mockshadow.lock.json').read_text(encoding='utf-8'))
    version = lock['version']
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[a-zA-Z0-9.]+)?', version):
        raise ValueError('Invalid pinned Mockshadow version')
    asset = lock['assets'].get(platform_key())
    if not asset:
        raise ValueError(f'No verified package pinned for {platform_key()}; set MOCKSHADOW_ROOT or update the lock.')
    if not re.fullmatch('[a-f0-9]{64}', asset['sha256']):
        raise ValueError('Invalid package SHA-256')
    cache = project / '.tools'
    root = cache / f'mockshadow-{version}-{platform_key()}-{asset["sha256"][:12]}'
    if cache.is_symlink() or cache.is_junction() or root.is_symlink() or root.is_junction():
        raise ValueError('Linked tool directories are not supported')
    if root.exists():
        verify(root, version)
        return root
    if not install:
        raise ValueError('Pinned Mockshadow is missing. Run setup_mockshadow.py first.')
    cache.mkdir(exist_ok=True)
    # Exclusive installation lock. No automatic deletion of another process's lock.
    gate = cache / '.mockshadow-install.lock'
    try:
        stream = gate.open('x')
    except FileExistsError:
        raise ValueError(f'Another installation may be running: {gate}') from None
    try:
        with stream:
            stream.write(str(os.getpid()))
        with tempfile.TemporaryDirectory(prefix='mockshadow-stage-', dir=cache) as scratch:
            scratch = Path(scratch)
            download = scratch / 'package.zip'
            if archive:
                shutil.copyfile(archive, download)
            else:
                if not asset['url'].startswith('https://'):
                    raise ValueError('Package downloads require HTTPS')
                print(f'Downloading Mockshadow {version} ({platform_key()})', file=sys.stderr)
                with urllib.request.urlopen(asset['url'], timeout=60) as response, download.open('wb') as output:
                    if not response.geturl().startswith('https://'):
                        raise ValueError('Insecure package redirect')
                    shutil.copyfileobj(response, output)
            if digest(download) != asset['sha256']:
                raise ValueError('Mockshadow package SHA-256 mismatch; nothing installed')
            stage = scratch / 'tool'
            stage.mkdir()
            extract(download, stage)
            verify(stage, version)
            subprocess.run([sys.executable, '-B', str(stage / 'mockshadow.py'), '--version'], check=True)
            probe = scratch / 'probe.c'
            probe.write_text('int mockshadow_probe(void) { return 1; }\n', encoding='ascii')
            result = subprocess.run([sys.executable, '-B', str(stage / 'clang-code-extractor/extract.py'),
                'function', 'mockshadow_probe', str(probe), 'lines'], capture_output=True,
                text=True, timeout=30, check=True)
            if result.stdout.strip() != '1;1':
                raise ValueError('Packaged extractor failed its installation probe')
            stage.rename(root)
    finally:
        gate.unlink()
    return root


def identity(root):
    root = Path(root)
    manifest = root / 'distribution.json'
    if manifest.is_file():
        return json.loads(manifest.read_text(encoding='utf-8'))['source']
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
    return {'commit': git('rev-parse', 'HEAD'), 'dirty': bool(git('status', '--porcelain'))}


def main(project=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=project or Path.cwd())
    parser.add_argument('--check', action='store_true', help='Verify without downloading')
    parser.add_argument('--archive', type=Path, help='Install an offline ZIP matching the lock')
    parser.add_argument('--local', help='Use an explicitly selected development checkout')
    args = parser.parse_args()
    try:
        print(resolve(args.project, args.local, install=not args.check, archive=args.archive))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Mockshadow setup: {error}\n')


if __name__ == '__main__':
    main()
