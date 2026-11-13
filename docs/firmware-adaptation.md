# Adapting firmware without changing its source

Mockshadow transforms copies of source through replacement/mock recipes. The
consumer supplies the simulation behavior, toolchain and runtime. It is not a CPU
instruction emulator, a peripheral library or a timing-equivalence guarantee.

## 1. Inventory and define success

Read the original build files, compiler/linker options, include paths, feature
defines, startup code and linker script. Record the original architecture, ABI,
endianness, language version and memory layout assumptions. Identify:

- Register access, volatile polling, inline assembly, barriers and DMA buffers.
- Interrupt entry points, priority/masking assumptions and callback ordering.
- Tasks, queues, notifications, critical sections and ISR-only operations.
- Tick sources, timeout units, rollover, watchdogs and busy waits.
- Communication framing, partial transfers, disconnects and error behavior.
- Persistent regions, erased values, write/erase rules and reboot semantics.

Choose native Windows/Linux or WebAssembly and a narrow observable goal: an input,
an application transition and an output. State which timing/order guarantees are
required and which hardware behavior is deliberately excluded. Build the original
when its tools are available; otherwise record that baseline as pending. Do not
edit it to make the simulation build pass.

## 2. Choose the boundary and implementation

| Choice | Suitable use | Required contract |
| --- | --- | --- |
| Stub | An intentionally unavailable or irrelevant operation | Explicit unsupported/error result, or documented no-op only when callers permit it |
| Stateful model | Registers, sampled input, output latches, queues, storage cells | Reset values, transitions, valid operations, bounds, faults and ordering |
| Functional implementation | Host files, sockets, thread synchronization, browser adapters | Real results plus failure, lifecycle, cancellation and platform behavior |

For each operation record inputs, outputs, side effects and failure semantics.
Preserve caller-visible status and callbacks. Unknown addresses, commands and
unsupported modes must produce a diagnostic with operation/context and a failure
or trap; if no error return exists, use an explicit fault mechanism. Avoid hangs
by making polling progress and timeout behavior deliberate. A log followed by
unconditional success is not a model.

Keep application logic in the original checkout. Put recipes under the consumer's
`mocks/`, ordinary models under `support/` (or another non-recipe directory), and
build/runtime adapters in consumer-owned files. Add files through explicit mappings.
Project-specific models stay in consumers; reusable examples here must be synthetic.

## 3. Create permanent inputs

Follow [README setup](../README.md#set-up-your-own-simulator). From the common parent
of a `mockshadow` checkout and `firmware` directory:

```sh
python mockshadow/mockshadow.py create-project simulator
cd simulator
```

Set `.mockshadow/env.json` to `{"originalProject":"../firmware"}`. Source and
simulator must be separate and non-nested. Track `.mockshadow/config.json` with
`formatVersion: 2`, `mocksDirectory: "mocks"`, additions, extraction flags and
copy rules. Keep env/output/cache ignored; do not commit local paths or reports
containing them. Check the scaffold before use; it is not a build system.

From the simulator root:

```sh
python ../mockshadow/mockshadow.py open-mock src/board.c --recipe hardware/board.c
python ../mockshadow/mockshadow.py list
python ../mockshadow/mockshadow.py audit --report reports/audit.json
python ../mockshadow/mockshadow.py mock --details
```

`src/board.c` must exist in that firmware; substitute a real inventoried target.
`open-mock` creates/finds a recipe skeleton, not a model. Follow the
[recipe contract](recipes.md) for metadata, encoding, phase order and flags.
Never assume textual order overrides transformation phases. Prefer replacing a
small function over an entire driver; use `replace` only when deliberately owning
the complete target. Do not put ordinary C helpers under `mocks/`.

Select includes/defines so the extractor sees the intended symbol. Extraction
flags and host build flags are separate inputs. The extractor parses after each
edit, may tolerate Clang diagnostics and chooses the first match; review ambiguous
symbols. [Architecture](architecture.md) describes why extraction must be sequential.
Do not run audit, mock or direct extraction concurrently on the same extractor
checkout. The per-project generation lock does not serialize different projects
or audits. Do not compile during publication.

For extractor diagnosis, from the Mockshadow root:

```sh
cd clang-code-extractor
python extract.py function ReadBattery ../examples/fixed-battery/firmware/adc.c lines
cd ..
```

Expected: `1;1`. The wrapper accepts `TYPE NAME SOURCE [extra_args]`, with `lines`
requesting line numbers. It uses the built extractor; it does not build one on
demand. Direct extraction writes `definition.txt`/`lines.txt` in its working
directory; the commands above keep them inside the submodule where they are
ignored. Mockshadow invokes it there too. Scratch output is not an input to commit.
Use the [extractor README](../clang-code-extractor/README.md) for dependencies and
build setup, and inspect `extract.py` when diagnosing wrapper behavior.

## 4. Validate and diagnose in layers

| Stage | Evidence | What it does not prove |
| --- | --- | --- |
| Audit | Each recipe applies to staged inputs; report has zero failures | Correct types, successful compilation or runtime behavior |
| Transformation | Successful `mock`; inspect transformed boundaries and mapped additions; originals unchanged | Complete or accurate hardware models |
| Compilation | Consumer build and link succeed for the named target | Initialization or functional correctness |
| Initialization | Process/module starts and reset state is observed | Steady-state behavior, real-time scheduling |
| Behavior | Known inputs cause expected outputs; errors, reset and state transitions checked | Equivalence beyond exercised cases |

Stop after a failed generation. A previous good `shadow_output` may still exist;
building it would test stale inputs. Rerun after correcting permanent inputs. Use
`mock --force` after changing external includes/toolchain libraries not hashed by
Mockshadow. Do not delete a lock without verifying its owner has stopped.

Classify failures before patching:

- **Transformation:** missing target/symbol, wrong flags, metadata, phase order or
  stale assumptions. Compare current original with recipe and generated result.
- **Model:** undefined state, missing callback, incorrect reset/error or unmodeled
  operation. Add a narrow, documented contract and an observable scenario.
- **Platform:** ABI, alignment, linking, scheduling, filesystem or browser API.
  Check the [native](targets/native.md) / [Wasm](targets/webassembly.md) guidance.
- **Possible application defect:** reproduce with controlled inputs and a checked
  model contract. Report separately; do not hide the symptom with a successful mock
  return or change original firmware under a simulation-only task.

## 5. Leave a reproducible handoff

Record toolchain versions, target architecture, exact working directory/commands,
scenario inputs/outputs, model reset rules, unsupported operations and current
limitations. Report each validation stage independently and label unavailable
platforms/tools as pending. Keep machine-specific logs outside versioned docs.
Use the [included examples](../examples/README.md) as a fresh-session exercise.
