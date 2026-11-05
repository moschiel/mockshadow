"""Apply the same inventory and operations as generation without publishing."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import time
from pipeline import prepare_inputs
from recipes import apply_recipe


def audit_project(project, original, config):
    sources, additions, recipes = prepare_inputs(project, original, config)
    started = time.monotonic()
    results = []
    with tempfile.TemporaryDirectory(prefix='mockshadow-audit-') as scratch:
        stage = Path(scratch)
        for relative, source in {**sources, **additions}.items():
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        for dest, recipe in sorted(recipes.items()):
            target = stage / dest
            before = target.read_bytes()
            entry = {'mock': recipe.path.relative_to(project).as_posix(), 'source': dest, 'mode': recipe.mode}
            diagnostics = io.StringIO()
            try:
                with contextlib.redirect_stdout(diagnostics), contextlib.redirect_stderr(diagnostics):
                    apply_recipe(recipe, original / dest, target)
                entry['status'] = 'ok'
            except (SystemExit, Exception) as error:
                target.write_bytes(before)
                entry.update(status='transform_failed', diagnostic=diagnostics.getvalue().strip() or str(error))
            results.append(entry)
            print(f"{entry['status']:18} {entry['mock']} -> {dest}", flush=True)
    failed = sum(item['status'] != 'ok' for item in results)
    return {'original_project': str(original), 'formatVersion': 2,
            'scope': 'First failure per recipe; later checks after a failure are provisional. No compile/runtime validation.',
            'files': len(results), 'passed': len(results) - failed, 'failed': failed,
            'elapsed_seconds': round(time.monotonic() - started, 2), 'results': results}


def run_audit(project, original, config, report_path=None):
    if report_path:
        report_path = report_path.resolve()
        protected = [original, project / config['mocksDirectory'], project / 'shadow_output', project / '.mockshadow']
        if any(report_path == root or root in report_path.parents for root in protected):
            raise ValueError('Audit report must be outside source, mocks, output and configuration')
        if report_path.suffix != '.json':
            raise ValueError('Audit report must be a JSON file')
        _, additions, _ = prepare_inputs(project, original, config)
        if report_path in (p.resolve() for p in additions.values()):
            raise ValueError('Audit report cannot overwrite an additional input')
    report = audit_project(project, original, config)
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f"Audit: {report['passed']}/{report['files']} passed; {report['failed']} failed")
    return 1 if report['failed'] else 0
