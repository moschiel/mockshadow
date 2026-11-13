# Mockshadow

Run C firmware on a host by replacing hardware-dependent code in a **separate
source tree**. Your simulator supplies models and a host build system. Mockshadow
transforms source; it does not emulate ARM instructions or invent device behavior.
It does not guarantee timing equivalence to hardware. Native Windows/Linux and
WebAssembly builds need consumer-owned models, build files and runtime adapters.

## Use with a coding agent

Ask an agent to read the versioned
[Mockshadow firmware skill](.agents/skills/mockshadow-firmware/SKILL.md) and follow
its linked docs. It guides inventory, model selection, recipes and validation
without requiring conversation history or a personal installation. Codex and
Claude Code discovery entries are included; see [agent integration](docs/agents.md)
for discovery scope and use from a new consumer project.

For daily use, keep firmware, simulator inputs and generated source separate.
After a firmware update, audit recipes, regenerate, compile and rerun behavioral
scenarios. Follow the [adaptation procedure](docs/firmware-adaptation.md), with
target guidance for [native](docs/targets/native.md) and
[WebAssembly](docs/targets/webassembly.md). The [examples](examples/README.md)
progress from a fixed battery replacement to a stateful, time-driven controller.

## Install

Use Python **3.12+**, Git, CMake and LLVM/Clang development libraries. Mockshadow
itself requires no Python packages. Install the platform dependencies in the
[extractor README](clang-code-extractor/README.md), then:

```sh
git clone --recurse-submodules https://github.com/moschiel/mockshadow.git
cd mockshadow
git submodule update --init --recursive
cd clang-code-extractor
python build.py
cd ..
python mockshadow.py --version
```

Windows: use MSYS2 **MINGW64** LLVM/GCC, put its `bin` on PATH, and match
`windows-config.cmake` to your installation. The extractor may be x64 even when
firmware requires x86. Linux: install matching Clang/LLVM development packages;
use `python3` if appropriate. Direct Python invocation needs no global install.
Legacy `setup.py` also builds the extractor but changes system setup on Linux.

## Run the fixed-battery example

From this repository, enter `examples/fixed-battery/simulator`. Copy
`.mockshadow/env.example.json` to `.mockshadow/env.json` using your editor,
PowerShell `Copy-Item` or Linux `cp`. Then:

```sh
python ../../../mockshadow.py mock
gcc shadow_output/main.c shadow_output/adc.c -I shadow_output -o fixed-battery
./fixed-battery
```

PowerShell: `./fixed-battery.exe`. Expected output: **battery=3700 mV**. The original ADC
returns zero; a symbol recipe substitutes a fixed model. A second `mock` reuses
the transformed file. Edit `support/__additional__battery.h`, then rerun.

## Set up your own simulator

```sh
python /path/to/mockshadow/mockshadow.py create-project my-simulator
cd my-simulator
```

Set ignored `.mockshadow/env.json` to:

```json
{ "originalProject": "../my-firmware-checkout" }
```

Firmware and simulator must be separate, **non-nested** directories. Relative
source paths resolve from the simulator root. Commit recipes, models, build
files and `.mockshadow/config.json`; keep local env and generated output ignored.

```json
{
  "formatVersion": 2,
  "mocksDirectory": "mocks",
  "additionalFiles": [],
  "extractorCFlags": ["-DDEVICE_FAMILY", "-DENABLE_ADC"],
  "excludeFromCopy": ["build", ".settings"],
  "addToCopy": [{"src": "host-kernel", "temp_dest": "FreeRTOS"}]
}
```

Exclusions are exact root-relative paths, not globs. VCS metadata is excluded
automatically. `addToCopy` replaces a destination subtree with a local dependency.

Mockshadow 2 requires `formatVersion: 2` and `mocksDirectory: "mocks"` in
config.json. Legacy projects must migrate; there is no filename-prefix fallback.
Add `additionalFiles: []` when there are no extra sources.

For source `src/adc.c`, create any C/C++ recipe, for example `mocks/sensors/battery.c`:

```c
//__MOCK_TARGET: src/adc.c
//__MOCK_MODE: patch
//__MOCK_REPLACE_CODE_START: function ReadBattery
int ReadBattery(void) { return 3700; }
//__MOCK_REPLACE_CODE_END
```

`patch` starts from the original. `replace` writes the recipe body, removing only
the two metadata lines. Both require an existing, included original target.
Metadata is mandatory in the initial comment header. One recipe owns each target;
C/C++ files inside mocksDirectory are recipes, so put ordinary helpers elsewhere.
Names and nesting are free; target paths use `/` relative to the original root.
See [recipe reference](docs/recipes.md) and [migration](docs/migration-v2.md).

Ordinary additional files use explicit mappings, without prefix semantics:

```json
"additionalFiles": [
  {"source": "support/battery.h", "destination": "host/battery.h"}
]
```

Destinations cannot collide with sources or other additions. `addToCopy` explicitly
replaces a dependency subtree; recipes cannot target excluded/replaced originals.

## CLI

Commands have no dash; options use `--` (or the documented short form).

```sh
python /path/to/mockshadow/mockshadow.py --help
python /path/to/mockshadow/mockshadow.py --version
python /path/to/mockshadow/mockshadow.py mock --details
python /path/to/mockshadow/mockshadow.py mock --force
python /path/to/mockshadow/mockshadow.py audit --report reports/audit.json
python /path/to/mockshadow/mockshadow.py list
python /path/to/mockshadow/mockshadow.py open-mock src/adc.c --recipe sensors/battery.c
```

`mock`: `-v/--details`, `-f/--force`. `audit`: `-r/--report`.
`open-mock` prints the existing/new recipe; `--editor code` also opens it.
`create-project NAME` creates an empty mocks directory and a version 2 config.
Every command accepts `-h/--help`. Unknown arguments fail with exit code 2;
operational errors return 1. Only successful generation permits a build.
Removed: positional `details`, `remock`, `version`, `clone-tree`, `clone-project`,
`unmock`, and the unfinished build/run/debug/exec/rebuild commands. Build and run
through the consumer. Use `mock --force` and `--version` instead.

Audit stages the same complete inputs and applies the same ordered operations as
mock, without publishing or modifying source, recipes, output or cache. Inventory
errors fail before transformation. Transformation failures are reported per recipe;
subsequent checks are provisional when an earlier recipe failed. Audit does not
prove compilation, signatures or runtime behavior.

## Cache and publication

Generation hashes source/addition content, recipes, configuration, Python tool
code and the extractor executable. Changed inputs conservatively invalidate all
recipes, including headers modified by another recipe. Cached
outputs are verified. Old dates or a branch switch cannot fool the cache;
`lastMockTimestamp` is ignored.

Changed output bytes receive a fresh timestamp so Make/Ninja rebuild even when
the source branch has old dates. Identical output preserves its previous date.

The entire tree is prepared under `.mockshadow/stage-*` and published only after
all recipes succeed. Failures preserve the last good `shadow_output`. Its
`.mockshadow-manifest.json` travels with it. Removed recipes restore source;
removed inputs disappear. Old generated files beside recipes are ignored:
inspect shadow_output, edit only recipes/models.

Publication uses same-volume renames with rollback. Do not compile while
generating or edit inputs mid-generation. A lock rejects concurrent generators.
After a forced termination, verify the process stopped, remove stale
`.mockshadow/generation.lock`, and rerun; interrupted publication is recovered.
Windows open file handles can prevent rename. No writable hardlinks are used;
symlink/junction inputs are rejected.

On Windows, sharing/lock violations are retried for up to five seconds per IO
operation. Python's CRT may report a lock as EACCES without a Windows error code;
that case is also retried, but persistent errors still fail. Recipe retries start
from a fresh source copy. Cleanup failures produce a warning with the remaining
directory, preserving the original diagnostic or a successful publication.

The extractor still parses per directive and takes the first matching symbol;
it may recover from Clang diagnostics. Sequential edits can change later parsing,
so naive batching would change semantics. See [architecture](docs/architecture.md).
Use `mock --force` after changing external includes/toolchain DLLs outside the hashed
inputs. Run audit/generation against one extractor checkout sequentially: its
upstream scratch files are shared.

## Maintenance

Missing symbols/text: inspect current source, recipe and preprocessor flags.
Never silently skip a failed replacement. Unknown IO: model its narrow hardware
boundary and preserve traps; success requires defined outputs and state.

Tests: `python -m unittest discover -s tests -v`. Agents start at
[AGENTS.md](AGENTS.md); all workflows also work without AI or personal skills.
