"""Resolve recipes by target, never by an inferred source-tree location."""
from pathlib import Path
import subprocess
from recipes import discover, local_path, relative_path
from source_types import SOURCE_EXTENSIONS


def open_mock(project, original, config, target, name=None, editor=None):
    target = relative_path(target).as_posix()
    if not local_path(original, target).is_file():
        raise ValueError(f'Original target does not exist: {target}')
    recipes = discover(project, config)
    if target in recipes:
        path = recipes[target].path
        if name:
            raise ValueError(f'A recipe already exists for {target}: {path}')
    else:
        root = project / config['mocksDirectory']
        path = local_path(root, name or Path(target).name)
        if path.suffix.lower() not in SOURCE_EXTENSIONS or Path(target).suffix.lower() not in SOURCE_EXTENSIONS:
            raise ValueError('Recipe and target must have a supported C/C++ extension')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('x', encoding='latin-1', newline='\n') as stream:
            stream.write(f'//__MOCK_TARGET: {target}\n//__MOCK_MODE: patch\n')
    print(path)
    if editor:
        subprocess.run([editor, str(path)], check=True)
    return path
