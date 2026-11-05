"""Version 2 recipe metadata and the shared transformation contract."""
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil

from source_types import SOURCE_EXTENSIONS


def relative_path(value):
    if (not isinstance(value, str) or not value or '\\' in value
            or PureWindowsPath(value).drive or value.startswith('/')
            or any(part in ('', '.', '..') for part in value.split('/'))
            or any(c in value for c in ':\x00')):
        raise ValueError(f'Expected a relative path using / without traversal: {value!r}')
    return Path(PurePosixPath(value))


def local_path(root, value):
    path = root / relative_path(value)
    for parent in [path, *path.parents]:
        if parent == root:
            break
        if parent.is_symlink() or parent.is_junction():
            raise ValueError(f'Linked input is not supported: {parent}')
    return path


def validate_config(config):
    if not isinstance(config, dict) or config.get('formatVersion') != 2:
        raise ValueError('Mockshadow requires formatVersion: 2. Migrate this project; legacy recipes are unsupported.')
    allowed = {'formatVersion', 'mocksDirectory', 'additionalFiles', 'extractorCFlags', 'excludeFromCopy', 'addToCopy'}
    if set(config) - allowed:
        raise ValueError(f'Unknown configuration fields: {sorted(set(config) - allowed)}')
    directory = relative_path(config.get('mocksDirectory'))
    if directory.parts[0].lower() in ('shadow_output', '.mockshadow', '.git', '.svn'):
        raise ValueError('mocksDirectory must be a dedicated input directory')
    for key in ('additionalFiles', 'extractorCFlags', 'excludeFromCopy', 'addToCopy'):
        if not isinstance(config.get(key, []), list):
            raise ValueError(f'{key} must be a list')
    for value in config.get('excludeFromCopy', []):
        relative_path(value)
    if any(not isinstance(flag, str) for flag in config.get('extractorCFlags', [])):
        raise ValueError('extractorCFlags must contain strings')
    return directory


@dataclass(frozen=True)
class Recipe:
    path: Path
    target: str
    mode: str
    body: bytes


def parse_recipe(path):
    lines = path.read_bytes().splitlines(keepends=True)
    fields, body = {}, []
    header = True
    block_comment = False
    for number, raw in enumerate(lines, 1):
        line = raw.decode('latin-1').strip()
        if '__MOCK_COPY_FILE_CONTENT__' in line or '__MOCK_DISCARD_FILE_CONTENT__' in line:
            raise ValueError(f'{path}:{number}: legacy mode marker; use __MOCK_MODE')
        match = re.fullmatch(r'//\s*__MOCK_(TARGET|MODE):\s*(.+)', line)
        if match:
            key, value = match.groups()
            if not header or key in fields:
                raise ValueError(f'{path}:{number}: duplicate or misplaced {key}')
            fields[key] = value.strip()
            continue
        if line.startswith('//__MOCK_TARGET') or line.startswith('//__MOCK_MODE'):
            raise ValueError(f'{path}:{number}: malformed metadata')
        if header:
            if block_comment:
                block_comment = '*/' not in line
            elif line.startswith('/*'):
                block_comment = '*/' not in line
            elif line and (not line.startswith('//') or '__MOCK_' in line):
                header = False
        body.append(raw)
    if set(fields) != {'TARGET', 'MODE'} or fields['MODE'] not in ('patch', 'replace'):
        raise ValueError(f'{path}: required __MOCK_TARGET and __MOCK_MODE: patch|replace')
    target = relative_path(fields['TARGET']).as_posix()
    if Path(target).suffix.lower() not in SOURCE_EXTENSIONS:
        raise ValueError(f'{path}: unsupported target extension: {target}')
    return Recipe(path, target, fields['MODE'], b''.join(body))


def discover(project, config):
    from pipeline import inventory
    directory = validate_config(config)
    root = local_path(project, directory.as_posix())
    if not root.is_dir():
        raise ValueError(f'Mocks directory does not exist: {root}')
    recipes, names = {}, {}
    for _, path in sorted(inventory(root).items()):
        if path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        recipe = parse_recipe(path)
        folded = recipe.target.casefold()
        if folded in names:
            raise ValueError(f'Duplicate target {recipe.target}: {names[folded]} and {path}')
        names[folded] = path
        recipes[recipe.target] = recipe
    return recipes


def apply_recipe(recipe, source, target, details=False):
    import mock_utils
    if recipe.mode == 'replace':
        target.write_bytes(recipe.body)
        return
    shutil.copy2(source, target)
    for transform in (mock_utils.mock_text_replace, mock_utils.mock_remove_content,
                      mock_utils.mock_replace_code, mock_utils.insert_mock_top_or_bottom,
                      mock_utils.mock_add_content_before_or_after):
        transform(str(recipe.path), str(target), details)
