# Native Windows and Linux consumers

Mockshadow supplies transformed source, mapped additions, audit and publication.
The consumer supplies compiler/linker settings, executable entry points, runtime
adapters, models, tests and any persistent data. The extractor is a separate host
tool: its architecture does not determine the simulated application's architecture.

## Build and ABI

Use the [installation instructions](../../README.md#install) for Python and the
Clang-based extractor. Choose a consumer compiler deliberately: GCC/Clang on Linux,
MinGW GCC/Clang or a separately validated MSVC build on Windows. The examples use
GCC-compatible C11 flags, not an MSVC command line.

Record compiler version, target triple and pointer width. Common 64-bit Linux
builds use LP64 (`long`/pointers 64 bits), while 64-bit Windows uses LLP64 (`long`
32 bits, pointers 64 bits). Check `sizeof`, signedness, packing and alignment in
the actual build. Use fixed-width integers for serialized data, `uintptr_t` for
pointer-sized arithmetic, and static assertions for required layouts. Do not
serialize host structs by accident or truncate pointers into firmware registers.
Choose a 32-bit build only when justified and all dependencies support it; it
does not reproduce the original processor's memory map or instruction behavior.

Exclude device startup/linker scripts and provide host startup in the consumer.
Compile generated sources only, with explicit source lists; avoid linking original
and replaced implementations together. Prefer warnings and supported sanitizers
to suppressing incompatibilities. Models must define register effects, not merely
allocate writable memory at familiar addresses.

## Execution, tasks and time

Decide whether to use a cooperative deterministic scheduler or a host RTOS/thread
port. Windows threads and POSIX threads do not automatically reproduce firmware
priorities, preemption or interrupt masking. Specify mutex/condition semantics,
wakeup ordering, queue bounds, shutdown and ISR-to-task delivery. Do not use
`volatile` as a replacement for thread synchronization.

Separate elapsed time from wall-clock timestamps. Use a monotonic host clock
(for example QueryPerformanceCounter or CLOCK_MONOTONIC), or inject a virtual
clock as the stateful example does. Define tick units, rollover and whether time
advances during blocking calls. Sleeping for a duration is not proof of a precise
deadline. Exercise timeout, cancellation and delayed-event paths.

## Communication and persistence

The consumer implements host transport adapters and specifies framing, partial
reads/writes, queueing, reconnects, EOF and backpressure. Windows sockets and POSIX
descriptors have different initialization/error/close APIs. A local socket bridge
does not model wire arbitration, electrical errors or peripheral DMA by itself.

For file-backed persistent regions, define size, erased value, valid ranges,
erase/write restrictions and reset-versus-power-cycle behavior. Use an explicit
data directory, detect short IO and corruption, and define flush/atomic-save
policy. A RAM array is volatile unless persistence is implemented. Keep generated
source cleanup separate from user data cleanup.

## Reproduce and qualify

From the Mockshadow root, run `python examples/verify.py --target native`.
Use `--cc clang` for a second compatible compiler. This checks transformation and
finite scenarios, without providing thread, transport or storage implementations.
See [example commands and outputs](../../examples/README.md).

Test each intended OS/ABI independently. A Windows x64 pass does not establish a
Linux, Windows x86 or MSVC pass. Record audit, transformation, compilation,
initialization and behavior separately using the [handoff checklist](../firmware-adaptation.md#5-leave-a-reproducible-handoff).
