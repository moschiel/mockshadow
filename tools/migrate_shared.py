"""Migrate verified project-local packages to the shared user installation."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
from mockshadow_bootstrap import user_home, platform_key, verify, resolve, install_command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, action='append', required=True)
    args = parser.parse_args()
    os.environ.pop("MOCKSHADOW_ROOT", None)
    projects = [p.resolve() for p in args.project]
    cache = user_home() / 'packages'
    if cache.is_symlink() or cache.is_junction():
        raise ValueError("Linked shared cache")
    cache.mkdir(parents=True, exist_ok=True)
    old = []
    for project in projects:
        local = project / '.tools'
        if local.is_symlink() or local.is_junction():
            raise ValueError(f'Refusing linked tools directory: {local}')
        lock = json.loads((project / 'mockshadow.lock.json').read_text(encoding='utf-8'))
        asset = lock['assets'][platform_key()]
        name = f'mockshadow-{lock["version"]}-{platform_key()}-{asset["sha256"][:12]}'
        source, destination = local / name, cache / name
        if source.exists() and not destination.exists():
            verify(source, lock['version'])
            # Both resolved paths are explicitly scoped before moving.
            if source.resolve().parent != local.resolve() or destination.resolve().parent != cache.resolve():
                raise ValueError('Unexpected migration path')
            if source.is_symlink() or source.is_junction():
                raise ValueError('Linked installation')
            shutil.move(str(source), str(destination))
        # Never delete old copies until every selected project resolves successfully.
        resolve(project, override=None, install=True)
        for candidate in local.glob('mockshadow-*'):
            if not re.fullmatch(r'mockshadow-[0-9]+\.[0-9]+\.[0-9]+-(windows|linux)-x64-[a-f0-9]{12}', candidate.name):
                continue
            if candidate.resolve().parent != local.resolve() or candidate.is_symlink() or candidate.is_junction():
                raise ValueError('Unexpected cleanup path')
            manifest = json.loads((candidate / 'distribution.json').read_text(encoding='utf-8'))
            verify(candidate, manifest['version'])
            old.append(candidate)
    install_command()
    for path in old:
        shutil.rmtree(path)
        print(f'Removed verified local package: {path}')
    for project in projects:
        local = project / '.tools'
        if local.exists() and not any(local.iterdir()):
            local.rmdir()
    print(f'Shared packages: {cache}')


if __name__ == '__main__':
    main()
