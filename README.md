# Mockshadow

Run C firmware on a host by replacing hardware-dependent code in a **separate
source tree**. Your simulator supplies models and a host build system. Mockshadow
transforms source; it does not emulate ARM instructions or invent device behavior.

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
python mockshadow.py version
```

Windows: use MSYS2 **MINGW64** LLVM/GCC, put its `bin` on PATH, and match
`windows-config.cmake` to your installation. The extractor may be x64 even when
firmware requires x86. Linux: install matching Clang/LLVM development packages;
use `python3` if appropriate. Direct Python invocation needs no global install.
Legacy `setup.py` also builds the extractor but changes system setup on Linux.

## Run the included example

From this repository, enter `examples/demo/simulator`. Copy
`.mockshadow/env.example.json` to `.mockshadow/env.json` using your editor,
PowerShell `Copy-Item` or Linux `cp`. Then:

```sh
python ../../../mockshadow.py mock
gcc TEMP_PROJECT/main.c TEMP_PROJECT/adc.c -I TEMP_PROJECT -o demo
./demo
```

PowerShell: `./demo.exe`. Expected output: **battery=3700 mV**. The original ADC
returns zero; a symbol recipe substitutes a fixed model. A second `mock` reuses
the transformed file. Edit `MOCK_TREE/__additional__battery.h`, then rerun.

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
  "extractorCFlags": ["-DDEVICE_FAMILY", "-DENABLE_ADC"],
  "excludeFromCopy": ["build", ".settings"],
  "addToCopy": [{"src": "host-kernel", "temp_dest": "FreeRTOS"}]
}
```

Exclusions are exact root-relative paths, not globs. VCS metadata is excluded
automatically. `addToCopy` replaces a destination subtree with a local dependency.

For source `src/adc.c`, create `MOCK_TREE/src/__mock__adc.c`:

```c
//__MOCK_COPY_FILE_CONTENT__
//__MOCK_REPLACE_CODE_START: function ReadBattery
int ReadBattery(void) { return 3700; }
//__MOCK_REPLACE_CODE_END
```

The copy marker must be the first line. Without it the recipe replaces the whole
file (discard mode), which still requires the original to exist. Review discard
recipes when upgrading firmware: they can hide upstream changes.

`MOCK_TREE/models/__additional__battery.c` becomes
`TEMP_PROJECT/models/__additional__battery.c`, with its name preserved. It is
ordinary C for model state, reset behavior and errors. Include it in your build.
The prefix identifies additional source, not a particular kind of model.
See [recipe reference](docs/recipes.md).

```sh
python /path/to/mockshadow/mockshadow.py audit --report reports/audit.json
python /path/to/mockshadow/mockshadow.py mock
# Build with your simulator's CMake/Make only after generation succeeds.
python /path/to/mockshadow/mockshadow.py remock
```

`audit` applies recipes to disposable files and reports the first failure per
file, continuing with the others; exit 1 means failure. It leaves source,
MOCK_TREE, TEMP_PROJECT and cache unchanged. `remock` bypasses the cache;
`details` adds diagnostics. Neither audit nor generation proves compilation,
signature compatibility or runtime behavior. Legacy `build/run/debug` commands
are placeholders: use the consuming simulator's build/launcher.

## Cache and publication

Generation hashes source/addition content, recipes, configuration, Python tool
code and the extractor executable. Changed inputs conservatively invalidate all
recipes, including headers modified by another recipe. Cached
outputs are verified. Old dates or a branch switch cannot fool the cache;
`lastMockTimestamp` is ignored.

Changed output bytes receive a fresh timestamp so Make/Ninja rebuild even when
the source branch has old dates. Identical output preserves its previous date.

The entire tree is prepared under `.mockshadow/stage-*` and published only after
all recipes succeed. Failures preserve the last good `TEMP_PROJECT`. Its
`.mockshadow-manifest.json` travels with it. Removed recipes restore source;
removed inputs disappear. Old generated files beside recipes are ignored:
inspect TEMP_PROJECT, edit only recipes/models.

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
Use `remock` after changing external includes/toolchain DLLs outside the hashed
inputs. Run audit/generation against one extractor checkout sequentially: its
upstream scratch files are shared.

## Maintenance

Missing symbols/text: inspect current source, recipe and preprocessor flags.
Never silently skip a failed replacement. Unknown IO: model its narrow hardware
boundary and preserve traps; success requires defined outputs and state.

Tests: `python -m unittest discover -s tests -v`. Agents start at
[AGENTS.md](AGENTS.md); all workflows also work without AI or personal skills.
