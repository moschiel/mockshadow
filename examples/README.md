# Reproducible examples

Each directory is named for the behavior it demonstrates. Both examples are synthetic.

| Example | What it teaches |
| --- | --- |
| `fixed-battery` | A symbol recipe replaces an ADC reading with a fixed value from an explicitly mapped header |
| `sampled-controller` | A board-boundary recipe delegates to a model with injected samples, virtual time, output state, reset and errors; the same model exposes a small C/JS API |

`fixed-battery` preserves the original minimal example's source and recipe content.
Build the extractor using the [root README](../README.md#install) first. Python
3.12+ and a GCC-compatible C11 compiler are needed; Wasm also needs an activated
Emscripten SDK and Node. Use `python3` where your system requires it.

## Repeatable checks

From the Mockshadow root:

```sh
python examples/verify.py --target native
python examples/verify.py --target native --cc clang
python examples/verify.py --target wasm
```

Run these sequentially, not in parallel. The verifier copies only fixture inputs
to temporary sibling firmware/simulator directories, creates env.json there,
runs real extractor-backed audit and generation, checks repeat-generation bytes
and input integrity, compiles and checks exact output plus error diagnostics.
It leaves existing example env/output files alone. Temporary reports/binaries are
removed on exit; no toolchains are downloaded. Missing tools or failed checks
return nonzero, never a skipped check reported as success. Each invocation may
take several seconds for Clang extraction. Do not run another extraction against
the same submodule checkout during verification.

## Manual native run

From `examples/sampled-controller/simulator`, copy `.mockshadow/env.example.json` to
`.mockshadow/env.json` with your editor, `Copy-Item` (PowerShell) or `cp` (Linux).
Then execute each command only after the previous one succeeds:

```sh
python ../../../mockshadow.py list
python ../../../mockshadow.py audit --report reports/audit.json
python ../../../mockshadow.py mock --details
gcc -std=c11 -Wall -Wextra -Werror shadow_output/app.c shadow_output/board.c shadow_output/sim_io.c shadow_output/check.c -I shadow_output -o sampled-controller
./sampled-controller
```

On PowerShell use `./sampled-controller.exe`. The audit reports one passing recipe and the
generation maps three additional files. `app.c`/headers remain byte-for-byte copies
of the firmware; `board.c` gets three function substitutions. Inspect these in
`shadow_output`, but correct only `mocks/board.c`, `support/` or config/build inputs.

Expected stdout:

```text
BOOT sampled-controller: time=0 output=0
PASS unavailable input
PASS samples: 250->0 750->1 100->0; period=10 ms
PASS invalid operations preserve state
PASS reset clears state
PASS uint32 clock rollover
```

Expected stderr (intentional negative cases, exit status still zero):

```text
model: invalid sample=-1
model: unsupported channel=7
model: null sample destination
model: invalid output=2
```

The C checks do not depend on `assert`/NDEBUG: any mismatch prints `FAIL` and
returns nonzero. The original board boundary returns unavailable/unsupported;
it cannot satisfy the behavioral checks without the recipe and added model.

## Model contract

| Input/action | Observable result |
| --- | --- |
| `sim_reset(); app_reset();` | Clock and output zero; no sample available |
| `sim_advance(10); app_step();` without injection | `BOARD_UNAVAILABLE` (-1); output unchanged |
| `sim_inject(250); app_step();` at the same time | Success (0); output remains off |
| Inject 750 without advancing time after success | `APP_IDLE` (1); output stays off |
| Advance another 10 ms and step | Success; output on |
| Inject 100, advance 10 ms, step | Success; output off |
| Sample outside 0..1000, null destination or output other than 0/1 | `BOARD_INVALID` (-3), diagnostic, prior state unchanged |
| Read channel other than 0 | `BOARD_UNSUPPORTED` (-2), diagnostic, destination unchanged |

Samples remain readable until overwritten or reset; this is a latch, not a queue.
The 32-bit millisecond clock wraps. Unsigned elapsed arithmetic is tested across
one wrap; calls must occur within one full clock cycle. `app_reset` resets sampling
time only; a simulated power-on calls both resets. All state is volatile. There
are no tasks, interrupts, transport, storage or electrical/analog effects. This
is a model-selection example, not a production HAL or cycle-accurate simulator.

## WebAssembly and JavaScript

The `--target wasm` verifier builds the same finite checks for Node, then a
modular ES module without `check.c`, and exercises exported C functions from
[sampled-controller/check-module.mjs](sampled-controller/check-module.mjs). The second check reports:

```text
BOOT wasm module: output=0
PASS wasm interop: input, time, output, rejection, reset
```

It also emits `model: invalid sample=-1` on stderr. To build a reusable module
manually after generation, from `examples/sampled-controller/simulator`:

```sh
emcc -std=c11 shadow_output/app.c shadow_output/board.c shadow_output/sim_io.c -I shadow_output --no-entry -sMODULARIZE=1 -sEXPORT_ES6=1 '-sENVIRONMENT=web,node' '-sEXPORTED_FUNCTIONS=_sim_reset,_sim_inject,_sim_advance,_sim_output,_app_reset,_app_step' -o model.mjs
node ../check-module.mjs ./model.mjs
```

Keep `model.mjs` beside its generated `model.wasm`. In a browser ES module served
over HTTP, the numeric API can be used as follows:

```js
import createModel from './model.mjs';
const model = await createModel();
model._sim_reset();
model._app_reset();
model._sim_inject(750);
model._sim_advance(10);
console.log(model._app_step(), model._sim_output()); // 0, 1
```

This snippet is an integration starting point. Node execution does not qualify
browser loading, event scheduling or deployment. See the
[WebAssembly target guide](../docs/targets/webassembly.md) for those checks and
[recorded validation](../docs/agent-integration-validation.md) for exercised platforms.
