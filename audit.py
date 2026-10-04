"""Exercise mock transformations on temporary files, without changing the shadow tree."""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import time

import mock_utils
from source_types import SOURCE_EXTENSIONS


def audit_project(original, mock_tree):
    """Report the first transformation failure in each file; continue with other files.

    This uses the same extractor and transformation order as `mock`. It is not a
    C compilation or a runtime/semantic check. Discard-mode files only need their
    original to exist, because Mockshadow copies their replacement verbatim.
    """
    results = []
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="mockshadow-audit-") as scratch:
        for mock in sorted(mock_tree.rglob("__mock__*")):
            if mock.suffix not in SOURCE_EXTENSIONS:
                continue
            relative = mock.relative_to(mock_tree)
            source_relative = relative.with_name(mock.name.removeprefix("__mock__"))
            source = original / source_relative
            entry = {"mock": relative.as_posix(), "source": source_relative.as_posix(),
                     "mode": mock_utils.check_file_mock_mode(str(mock))}
            output = io.StringIO()
            if not source.is_file():
                entry.update(status="missing_source", diagnostic="Original file does not exist")
            else:
                entry["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
                destination = Path(scratch) / source_relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                try:
                    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                        if entry["mode"] == "copy":
                            for transform in (mock_utils.mock_text_replace,
                                              mock_utils.mock_remove_content,
                                              mock_utils.mock_replace_code,
                                              mock_utils.insert_mock_top_or_bottom,
                                              mock_utils.mock_add_content_before_or_after):
                                transform(str(mock), str(destination), False)
                    entry["status"] = "ok"
                except (SystemExit, Exception) as error:
                    entry.update(status="transform_failed", diagnostic=output.getvalue().strip()
                                 or str(error))
            results.append(entry)
            print(f"{entry['status']:18} {relative.as_posix()}", flush=True)
    failed = sum(item["status"] != "ok" for item in results)
    return {"original_project": str(original), "mock_tree": str(mock_tree),
            "scope": "First failure per mock file; no compile or runtime validation",
            "files": len(results), "passed": len(results) - failed, "failed": failed,
            "elapsed_seconds": round(time.monotonic() - started, 2), "results": results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Write a JSON report outside the original tree")
    args = parser.parse_args(argv)
    import runtime
    original = Path(runtime.USER_ENV["originalProject"]).resolve()
    mock_tree = Path(runtime.DIR_SHADOW_MOCKS).resolve()
    if not mock_tree.is_dir():
        parser.error(f"Mock tree does not exist: {mock_tree}")
    if args.report and (args.report.resolve() == original or original in args.report.resolve().parents):
        parser.error("The report must be outside the original source tree")
    report = audit_project(original, mock_tree)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Audit: {report['passed']}/{report['files']} files passed; {report['failed']} failed")
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
