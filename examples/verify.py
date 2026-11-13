#!/usr/bin/env python3
"""Verify real recipes and finite scenarios in temporary copies, sequentially."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STATEFUL_OUTPUT = [
    "BOOT sampled-controller: time=0 output=0",
    "PASS unavailable input",
    "PASS samples: 250->0 750->1 100->0; period=10 ms",
    "PASS invalid operations preserve state",
    "PASS reset clears state",
    "PASS uint32 clock rollover",
]
STATEFUL_ERRORS = [
    "model: invalid sample=-1",
    "model: unsupported channel=7",
    "model: null sample destination",
    "model: invalid output=2",
]
EXPORTS = ["_sim_reset", "_sim_inject", "_sim_advance", "_sim_output",
           "_app_reset", "_app_step"]


def snapshot(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()}


def run(command, cwd):
    print("+ " + subprocess.list2cmdline([str(part) for part in command]), flush=True)
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=180)
    if result.stdout:
        print(result.stdout.rstrip(), flush=True)
    if result.stderr:
        print('[command stderr]\n' + result.stderr.rstrip(), flush=True)
    if result.returncode:
        raise RuntimeError(f"Command failed with exit code {result.returncode}")
    return result


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify(name, args, scratch):
    source = ROOT / 'examples' / name
    base = scratch / name
    original = base / 'firmware'
    project = base / 'simulator'
    shutil.copytree(source / 'firmware', original)
    for part in ('mocks', 'support'):
        shutil.copytree(source / 'simulator' / part, project / part)
    config = project / '.mockshadow'
    config.mkdir()
    shutil.copy2(source / 'simulator/.mockshadow/config.json', config / 'config.json')
    shutil.copy2(source / 'simulator/.mockshadow/env.example.json', config / 'env.json')
    before_source, before_inputs = snapshot(original), snapshot(project)
    cli = [sys.executable, str(ROOT / 'mockshadow.py')]
    report = base / 'audit.json'
    run(cli + ['audit', '--report', str(report)], project)
    data = json.loads(report.read_text(encoding='utf-8'))
    require(data['files'] == 1 and data['failed'] == 0, 'Unexpected audit result')
    require(snapshot(project) == before_inputs, 'Audit changed simulator inputs/output')
    print(f"PASS {name}: audit", flush=True)
    run(cli + ['mock'], project)
    shadow = project / 'shadow_output'
    first = snapshot(shadow)
    require((shadow / ('adc.c' if name == 'fixed-battery' else 'board.c')).read_bytes()
            != (original / ('adc.c' if name == 'fixed-battery' else 'board.c')).read_bytes(),
            'Recipe did not change the hardware boundary')
    run(cli + ['mock'], project)
    require(snapshot(shadow) == first, 'Repeat generation changed output bytes')
    require(snapshot(original) == before_source, 'Original source changed')
    after_inputs = snapshot(project)
    for relative, digest in before_inputs.items():
        require(after_inputs.get(relative) == digest, f'Input changed: {relative}')
    print(f"PASS {name}: transformation, repeat generation, original/input integrity", flush=True)

    sources = (['main.c', 'adc.c'] if name == 'fixed-battery'
               else ['app.c', 'board.c', 'sim_io.c', 'check.c'])
    common = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(shadow)]
    compiler = args.cc if args.target == 'native' else args.emcc
    artifact = base / (name + ('.exe' if os.name == 'nt' else '')
                       if args.target == 'native' else name + '.js')
    command = [compiler, *common, *[str(shadow / p) for p in sources]]
    if args.target == 'wasm':
        command += ['-sENVIRONMENT=node', '-sEXIT_RUNTIME=1']
    run([*command, '-o', str(artifact)], project)
    print(f"PASS {name}: compilation ({args.target})", flush=True)
    result = run([str(artifact)] if args.target == 'native'
                 else [args.node, str(artifact)], project)
    output = result.stdout.splitlines()
    expected = ['battery=3700 mV'] if name == 'fixed-battery' else STATEFUL_OUTPUT
    require(bool(output) and output[0] == expected[0], 'Initialization marker mismatch')
    print(f"PASS {name}: initialization", flush=True)
    require(output == expected, 'Behavior output mismatch')
    require(result.stderr.splitlines() == ([] if name == 'fixed-battery' else STATEFUL_ERRORS),
            'Expected explicit model diagnostics differ')
    print(f"PASS {name}: behavior", flush=True)

    if args.target == 'wasm' and name == 'sampled-controller':
        module = base / 'model.mjs'
        run([args.emcc, *common, *[str(shadow / p) for p in sources if p != 'check.c'],
             '--no-entry', '-sMODULARIZE=1', '-sEXPORT_ES6=1', '-sENVIRONMENT=web,node',
             '-sEXPORTED_FUNCTIONS=' + json.dumps(EXPORTS, separators=(',', ':')),
             '-o', str(module)], project)
        print('PASS sampled-controller: C/JS module compilation', flush=True)
        interop = run([args.node, str(source / 'check-module.mjs'), str(module)], project)
        require(interop.stdout.splitlines() == [
            'BOOT wasm module: output=0',
            'PASS wasm interop: input, time, output, rejection, reset'],
            'C/JS behavior output mismatch')
        require(interop.stderr.splitlines() == ['model: invalid sample=-1'],
                'C/JS diagnostic mismatch')
        print('PASS sampled-controller: C/JS initialization and behavior (Node)', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=('native', 'wasm'), default='native')
    parser.add_argument('--cc', default='gcc', help='GCC-compatible native compiler executable')
    parser.add_argument('--emcc', default='emcc', help='Activated Emscripten compiler executable')
    parser.add_argument('--node', default='node', help='Node executable for Wasm checks')
    args = parser.parse_args()
    try:
        for program in ([args.cc] if args.target == 'native' else [args.emcc, args.node]):
            require(shutil.which(program) is not None, f'Required tool unavailable: {program}')
        with tempfile.TemporaryDirectory(prefix='mockshadow-examples-') as temporary:
            for name in ('fixed-battery', 'sampled-controller'):
                verify(name, args, Path(temporary))
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1
    print(f'PASS examples ({args.target}); browser qualification is separate')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
