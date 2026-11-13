# Agent integration validation

Validation date: 2026-11-12. These results describe the initial repository skill
and synthetic examples, not arbitrary consumer firmware or hardware equivalence.

## Environment and commands

Windows x64; Python 3.13.4; MinGW GCC 15.2.0; Clang 21.1.1 targeting
`x86_64-w64-windows-gnu`; Emscripten 6.0.5; Node 24.22.2. An existing Emscripten
SDK was activated for the Wasm run. No toolchain installation was performed.

From the Mockshadow root, run sequentially:

```sh
python -m unittest discover -s tests -v
python examples/verify.py --target native
python examples/verify.py --target native --cc clang
python examples/verify.py --target wasm
```

The Python suite passed all 14 tests. The example verifier uses the real built
extractor, in addition to the suite's isolated regression fixtures.
The documented manual Emscripten/Node module commands also passed in PowerShell;
comma-containing settings are quoted for shell portability. A deliberately
missing compiler made the verifier exit with code 1 before starting generation.

## Results by layer

| Layer | Windows native | WebAssembly under Node |
| --- | --- | --- |
| Audit | Both examples: 1/1 recipe passes | Both examples: 1/1 recipe passes |
| Transformation | Real symbol substitutions, additions, stable repeat generation, input/source integrity pass | Same checks pass on the Windows development host |
| Compilation | Both examples pass C11 warnings-as-errors with GCC and Clang | Both finite executables and the exported controller ES module compile with Emscripten |
| Initialization | Expected initial output/reset state observed | Expected C executable and JavaScript-created module startup observed |
| Behavior | Fixed battery value; unavailable input; 10 ms sampling; low/high/low output; invalid operations; reset; clock rollover | Same finite C scenarios plus numeric C/JS input, time, output, rejection and reset checks |

Expected errors are asserted alongside output; they are not suppressed to make
the run pass. The verifier prints captured command stderr under a label so that
intentional model diagnostics remain readable alongside stage results.

## Portability and fresh-session review

Both SKILL.md files passed the skill frontmatter validator. Relative file links,
CLI usage and recipe metadata were checked against the current repository. A
fresh agent given only the canonical skill location and a request to reproduce
the example followed the documentation and passed the Clang native verifier.
It also identified the then-missing link to this report; this report resolves it.

The two directories now use behavior-specific names, `fixed-battery` and
`sampled-controller`. The original fixed-battery fixture files retain their
content; commands and links use the new location. The GCC and Wasm checks were
rerun after renaming. No original consumer firmware was changed or used as a
fixture. New source, recipes and prose were reviewed for private identifiers,
paths, protocols and copied content; none were introduced.

## Extractor and remaining checks

The extractor was inspected and used, without modifications or a gitlink change:
`cb3d1033d2cdfa387be79a53444f3197f0687eda`. No missing interface was needed for
this delivery. Its shared scratch files require serial execution. The existing
built extractor was used; a clean extractor/toolchain rebuild was not performed.

Linux execution remains pending: WSL returned `E_ACCESSDENIED` in this environment.
Windows x86 and MSVC were not exercised. Browser execution/deployment remains
pending; Node results do not verify browser scheduling, loading or storage.
Client automatic discovery was documented from the official references in
[agents.md](agents.md), but Codex/Claude UI discovery was not exercised. Explicit
file reading was exercised without account installation. No push, merge or
publication is part of this validation.
