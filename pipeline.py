"""Content-addressed generation with staged publication of the complete shadow."""
from contextlib import contextmanager
import hashlib
import errno
import json
import os
from pathlib import Path
import shutil
import tempfile
import time

import mock_utils
from recipes import relative_path, local_path, validate_config, discover, apply_recipe

MANIFEST = ".mockshadow-manifest.json"
VERSION = 2


def retry_io(operation, *args, timeout=5.0, **kwargs):
    """Bounded retry for Windows locks, including CRT's lossy EACCES mapping."""
    deadline = time.monotonic() + timeout
    delay = 0.05
    while True:
        try:
            return operation(*args, **kwargs)
        except OSError as error:
            winerror = getattr(error, "winerror", None)
            transient = winerror in (5, 32, 33) or (
                os.name == "nt" and winerror is None and error.errno == errno.EACCES)
            if not transient or time.monotonic() >= deadline:
                raise
            time.sleep(min(delay, max(0, deadline - time.monotonic())))
            delay = min(delay * 2, 0.5)


@contextmanager
def staging_directory(parent):
    path = Path(tempfile.mkdtemp(prefix="stage-", dir=parent))
    try:
        yield path
    finally:
        try:
            retry_io(shutil.rmtree, path)
        except OSError as error:
            # Cleanup must not obscure the transformation error or turn an
            # already-published generation into a reported generation failure.
            print(f"Warning: staging cleanup deferred for {path}: {error}")


def digest(path):
    def read():
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()
    return retry_io(read)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def inventory(root, excludes=()):
    """Exact root-relative exclusions, plus VCS metadata; never follow links."""
    result = {}
    excludes = {str(p).replace("\\", "/").strip("/") for p in excludes}
    for current, dirs, files in os.walk(root):
        current = Path(current)
        for name in list(dirs) + files:
            path = current / name
            rel = path.relative_to(root).as_posix()
            if name in (".git", ".svn") or rel in excludes:
                if name in dirs:
                    dirs.remove(name)
                continue
            if path.is_symlink() or path.is_junction():
                raise ValueError(f"Linked inputs are not supported: {path}")
            if name in files:
                result[rel] = path
    return result


@contextmanager
def project_lock(project):
    lock = project / ".mockshadow/generation.lock"
    try:
        stream = lock.open("x")
    except FileExistsError:
        raise RuntimeError(f"Another generation may be running. If it crashed, remove {lock}") from None
    try:
        with stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


def generate(project, original, config, force=False, details=False):
    project, original = Path(project).resolve(), Path(original).resolve()
    if project == original or project in original.parents or original in project.parents:
        raise ValueError("Firmware and simulator must be separate, non-nested directories")
    if not original.is_dir():
        raise ValueError(f"Original source directory does not exist: {original}")
    tree = local_path(project, validate_config(config).as_posix())
    if not tree.is_dir():
        raise ValueError(f"Mock tree does not exist: {tree}")
    output = project / "shadow_output"
    backup = project / ".mockshadow/previous-tree"
    for path in (tree, output, backup, project / ".mockshadow"):
        if path.is_symlink() or path.is_junction():
            raise ValueError(f"Linked output/configuration directory is unsafe: {path}")
    with project_lock(project):
        # Recover an interrupted rename before attempting any new work.
        if backup.exists():
            if not output.exists():
                retry_io(backup.rename, output)
            else:
                retry_io(shutil.rmtree, backup)
        return _generate(project, original, config, tree, output, backup, force, details)


def prepare_inputs(project, original, config):
    if project == original or project in original.parents or original in project.parents:
        raise ValueError('Firmware and simulator must be separate, non-nested directories')
    if not original.is_dir():
        raise ValueError(f'Original source directory does not exist: {original}')
    validate_config(config)
    recipes = discover(project, config)
    sources = inventory(original, config.get("excludeFromCopy", []))
    originals = dict(sources)
    output = project / "shadow_output"
    dependency_destinations = []
    for item in config.get("addToCopy", []):
        if not isinstance(item, dict) or set(item) != {'src', 'temp_dest'}:
            raise ValueError('addToCopy entries require src and temp_dest')
        destination = relative_path(item["temp_dest"]).as_posix()
        folded = destination.casefold()
        if any(folded == old or folded.startswith(old + '/') or old.startswith(folded + '/')
               for old in dependency_destinations):
            _collision(destination)
        dependency_destinations.append(folded)
        source = local_path(project, item["src"])
        if not source.is_dir():
            raise ValueError(f"Missing addToCopy directory: {source}")
        # Local dependencies like FreeRTOS are valid; generated/config inputs are not.
        private = project / ".mockshadow"
        if (source == project or source in project.parents or source == output
                or output in source.parents or source == private or private in source.parents):
            raise ValueError(f"Unsafe addToCopy source: {source}")
        sources = {k: v for k, v in sources.items() if k != destination and not k.startswith(destination + "/")}
        sources.update({f"{destination}/{k}": v for k, v in inventory(source).items()})
    additions = {}
    for item in config.get('additionalFiles', []):
        if not isinstance(item, dict) or set(item) != {'source', 'destination'}:
            raise ValueError('additionalFiles entries require source and destination')
        source = local_path(project, item['source'])
        if source.relative_to(project).parts[0] in ('shadow_output', '.mockshadow'):
            raise ValueError(f'Generated/config input is not allowed: {source}')
        if not source.is_file():
            raise ValueError(f'Missing additional file: {source}')
        destination = relative_path(item['destination']).as_posix()
        additions[destination] = source if destination not in additions else _collision(destination)
    destinations = {}
    for dest in [*sources, *additions]:
        folded = dest.casefold()
        if folded in destinations:
            _collision(dest)
        destinations[folded] = dest
    for dest in destinations:
        parts = dest.split('/')
        if parts[0] in ('.git', '.svn', '.mockshadow') or dest == MANIFEST:
            raise ValueError(f'Reserved output path: {dest}')
        if any('/'.join(parts[:i]) in destinations for i in range(1, len(parts))):
            _collision(dest)
    for dest, recipe in recipes.items():
        if dest not in originals:
            raise ValueError(f'{recipe.path}: target missing or excluded from original: {dest}')
        if dest not in sources or sources[dest] != originals[dest]:
            raise ValueError(f'{recipe.path}: target replaced by addToCopy: {dest}')
    return sources, additions, recipes


def _collision(destination):
    raise ValueError(f'Output destination collision: {destination}')


def _generate(project, original, config, tree, output, backup, force, details):
    sources, additions, recipes = prepare_inputs(project, original, config)

    tool_root = Path(__file__).parent
    tool_files = list(tool_root.glob("*.py")) + list((tool_root / "clang-code-extractor").glob("*.py"))
    tool_files += list((tool_root / "clang-code-extractor/build").glob("extractor*"))
    context = fingerprint({"version": VERSION, "original": str(original), "config": config,
        "sources": {k: digest(v) for k, v in sources.items()},
        "additions": {k: digest(v) for k, v in additions.items()},
        # A recipe can alter a header included by another transformation. Until
        # the extractor reports dependencies, invalidate conservatively.
        "recipes": {k: [v.mode, digest(v.path)] for k, v in recipes.items()},
        "tools": {str(p.relative_to(tool_root)): digest(p) for p in tool_files if p.is_file()}})
    previous = {}
    try:
        previous = json.loads((output / MANIFEST).read_text(encoding="utf-8"))
        if not isinstance(previous, dict) or previous.get("version") != VERSION or not isinstance(previous.get("recipes"), dict):
            previous = {}
    except (FileNotFoundError, ValueError):
        pass
    entries = {}
    reused = 0
    # Same volume as output: two directory renames, with rollback on publication failure.
    with staging_directory(project / ".mockshadow") as temporary:
        stage = Path(temporary) / "tree"
        stage.mkdir()
        for rel, source in {**sources, **additions}.items():
            target = stage / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            retry_io(shutil.copy2, source, target)
        for dest, recipe in sorted(recipes.items()):
            rel = recipe.path.relative_to(project).as_posix()
            source = original / dest
            if not source.is_file():
                raise ValueError(f"Missing source for {rel}: {source}")
            target = stage / dest
            target.parent.mkdir(parents=True, exist_ok=True)
            key = fingerprint([context, dest, digest(source), digest(recipe.path), recipe.mode])
            old = previous.get("recipes", {}).get(dest, {})
            if not isinstance(old, dict):
                old = {}
            cached = output / dest
            if not force and old.get("key") == key and cached.is_file() and digest(cached) == old.get("output"):
                retry_io(shutil.copy2, cached, target)
                reused += 1
            else:
                print(f"Transform: {rel}", flush=True)
                retry_io(apply_recipe, recipe, source, target, details)
                # Preserve build timestamps when a forced transformation produces identical bytes.
                if cached.is_file() and digest(cached) == digest(target):
                    retry_io(shutil.copystat, cached, target)
            entries[dest] = {"recipe": rel, "mode": recipe.mode, "destination": dest, "key": key, "output": digest(target)}
        # Make/Ninja still use mtimes even though our cache uses hashes. Copying
        # old branch timestamps onto changed bytes would leave stale objects.
        for rel, target in inventory(stage).items():
            old_output = output / rel
            if old_output.is_file() and digest(target) == digest(old_output):
                retry_io(shutil.copystat, old_output, target)
            else:
                retry_io(os.utime, target, None)
        manifest = {"version": VERSION, "context": context, "recipes": entries}
        retry_io((stage / MANIFEST).write_text, json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        if output.exists():
            retry_io(output.rename, backup)
        try:
            retry_io(stage.rename, output)
        except BaseException:
            if backup.exists():
                retry_io(backup.rename, output)
            raise
        if backup.exists():
            try:
                retry_io(shutil.rmtree, backup)
            except OSError as error:
                print(f"Warning: previous-tree cleanup deferred for {backup}: {error}")
    print(f"Published shadow_output: {len(entries)} recipes, {reused} reused; {len(additions)} additions")
    return manifest
