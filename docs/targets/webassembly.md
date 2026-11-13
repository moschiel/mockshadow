# WebAssembly consumers

Mockshadow still runs on the development host and produces C source. It does not
emit Wasm, export functions to JavaScript, schedule browser work or implement
browser peripheral models. The consumer supplies those parts using a toolchain
such as Emscripten. A native Clang extractor is still needed for symbol recipes.

## Toolchain and C/JavaScript boundary

Activate an installed Emscripten SDK and check `emcc --version` and `node --version`.
Do not silently download a toolchain from a simulator script. From the Mockshadow
root, `python examples/verify.py --target wasm` compiles and runs finite C scenarios
under Node. The [example guide](../../examples/README.md) also supplies a modular
build and JavaScript calls into the stateful model.

Export only the intended C entry points. Await module initialization before calling
them; define ownership and lifetime of strings/buffers crossing the boundary.
Keep pointer/length contracts explicit and validate ranges on both sides. A C
pointer refers into linear memory, not a JavaScript object. If memory grows,
reacquire typed-array views rather than holding views into the old buffer.
Select stack/heap limits and decide whether growth is allowed. Check the actual
target's pointer/integer sizes; do not assume host ABI or cast JavaScript Numbers
to arbitrary 64-bit values without a deliberate conversion contract.

## Execution and time

Use bounded steps, an event loop or an explicitly designed asynchronous runtime.
A firmware `while (1)` with busy polling can block browser events and prevent its
own inputs from arriving. Expose initialization, input injection, bounded stepping
and state reads, or use Emscripten's main-loop facilities. Asyncify/JSPI and workers
are consumer design choices, not Mockshadow features.

Virtual time makes scenarios repeatable; real-time browser timers can be delayed
or throttled, especially in background tabs. State whether one step advances
virtual time or reads a host clock. Test cancellation, pause/resume, reset and
bounded work per callback. Do not claim MCU interrupt latency or cycle accuracy.

Threads need a separate design and deployment validation. Emscripten pthreads
depend on shared-memory/worker support and appropriate cross-origin isolation
headers. Avoid blocking the browser main thread. A single-threaded Node run does
not validate browser threads, timing or response to tab suspension.

## Browser IO and persistence

Browsers do not provide arbitrary raw TCP/UDP sockets or memory-mapped device IO.
Use an explicit supported transport (for example WebSocket/HTTP with a bridge),
with asynchronous completion, bounded queues and disconnect/error handling.
Device APIs depend on browser support, permissions and deployment context.

Treat virtual filesystem data as volatile unless a persistent backend is configured
and synchronized. Define loading before initialization, save completion, quota
errors and reset-versus-reload behavior. Do not report a save as durable merely
because a C memory buffer changed. These models/adapters belong in the consumer.

## Validation boundary

The provided Wasm checks cover a Node-hosted module and numeric C/JS calls. To
qualify a browser consumer, also serve its assets over HTTP, await module loading,
inject a known input, step it, read the output and test failed loading/disconnects.
Inspect the browser console, memory growth and responsiveness. Test deployment
headers if workers/shared memory are used. Report unavailable browser checks as
pending, independently of successful audit, generation or Node execution.

Toolchain references:
[runtime environment](https://emscripten.org/docs/porting/emscripten-runtime-environment.html),
[C/JavaScript interop](https://emscripten.org/docs/porting/connecting_cpp_and_javascript/Interacting-with-code.html),
[pthreads](https://emscripten.org/docs/porting/pthreads.html),
[filesystem](https://emscripten.org/docs/api_reference/Filesystem-API.html).
