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

MANIFEST = ".mockshadow-manifest.json"
VERSION = 1


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


def relative_path(value):
    path = Path(value)
    if path.is_absolute() or not path.parts or ".." in path.parts or path.drive:
        raise ValueError(f"Expected a relative destination inside the shadow: {value}")
    return path


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
    tree = project / "MOCK_TREE"
    if not tree.is_dir():
        raise ValueError(f"Mock tree does not exist: {tree}")
    output = project / "TEMP_PROJECT"
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


def _generate(project, original, config, tree, output, backup, force, details):
    sources = inventory(original, config.get("excludeFromCopy", []))
    for item in config.get("addToCopy", []):
        destination = relative_path(item["temp_dest"]).as_posix()
        source = (project / item["src"]).resolve()
        if not source.is_dir():
            raise ValueError(f"Missing addToCopy directory: {source}")
        # Local dependencies like FreeRTOS are valid; generated/config inputs are not.
        private = project / ".mockshadow"
        if (source == project or source in project.parents or source == output
                or output in source.parents or source == private or private in source.parents):
            raise ValueError(f"Unsafe addToCopy source: {source}")
        sources = {k: v for k, v in sources.items() if k != destination and not k.startswith(destination + "/")}
        sources.update({f"{destination}/{k}": v for k, v in inventory(source).items()})
    mock_files = inventory(tree)
    recipes = {k: v for k, v in mock_files.items() if v.name.startswith("__mock__") and v.suffix in (".c", ".h")}
    additions = {k: v for k, v in mock_files.items() if v.name.startswith("__additional__") and v.suffix in (".c", ".h")}
    tool_root = Path(__file__).parent
    tool_files = list(tool_root.glob("*.py")) + list((tool_root / "clang-code-extractor").glob("*.py"))
    tool_files += list((tool_root / "clang-code-extractor/build").glob("extractor*"))
    context = fingerprint({"version": VERSION, "original": str(original), "config": config,
        "sources": {k: digest(v) for k, v in sources.items()},
        "additions": {k: digest(v) for k, v in additions.items()},
        # A recipe can alter a header included by another transformation. Until
        # the extractor reports dependencies, invalidate conservatively.
        "recipes": {k: digest(v) for k, v in recipes.items()},
        "tools": {str(p.relative_to(tool_root)): digest(p) for p in tool_files if p.is_file()}})
    previous = {}
    try:
        previous = json.loads((output / MANIFEST).read_text(encoding="utf-8"))
        if not isinstance(previous, dict) or not isinstance(previous.get("recipes"), dict):
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
        for rel, recipe in sorted(recipes.items()):
            dest = Path(rel).with_name(recipe.name.removeprefix("__mock__")).as_posix()
            source = original / dest
            if not source.is_file():
                raise ValueError(f"Missing source for {rel}: {source}")
            target = stage / dest
            target.parent.mkdir(parents=True, exist_ok=True)
            key = fingerprint([context, dest, digest(source), digest(recipe)])
            old = previous.get("recipes", {}).get(rel, {})
            if not isinstance(old, dict):
                old = {}
            cached = output / dest
            if not force and old.get("key") == key and cached.is_file() and digest(cached) == old.get("output"):
                retry_io(shutil.copy2, cached, target)
                reused += 1
            else:
                print(f"Transform: {rel}", flush=True)
                def transform_file():
                    if mock_utils.check_file_mock_mode(str(recipe)) == "copy":
                        retry_io(shutil.copy2, source, target)
                        for transform in (mock_utils.mock_text_replace, mock_utils.mock_remove_content,
                                          mock_utils.mock_replace_code, mock_utils.insert_mock_top_or_bottom,
                                          mock_utils.mock_add_content_before_or_after):
                            transform(str(recipe), str(target), details)
                    else:
                        retry_io(shutil.copy2, recipe, target)
                retry_io(transform_file)
                # Preserve build timestamps when a forced transformation produces identical bytes.
                if cached.is_file() and digest(cached) == digest(target):
                    retry_io(shutil.copystat, cached, target)
            entries[rel] = {"destination": dest, "key": key, "output": digest(target)}
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
    print(f"Published TEMP_PROJECT: {len(entries)} recipes, {reused} reused; {len(additions)} additions")
    return manifest
