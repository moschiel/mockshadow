# Portable distribution

Python 3.12+ is required. Consumers do not need Git, CMake, a C++ compiler or
LLVM development libraries to run a released Mockshadow package. Their own
firmware toolchains and firmware headers remain separate dependencies.

Packages contain Python sources, templates/docs, the native extractor, Clang
builtin headers, dependent runtime libraries and third-party notices. Windows
x64 and Ubuntu 24.04 x64 have separate ZIPs. Other platforms need a source build.
No binaries are committed to Git. Source builds remain supported.

## Consumer integration

Vendor `tools/mockshadow_bootstrap.py` unchanged into the consumer's scripts
directory. Record exact release URLs and SHA-256 values in
`mockshadow.lock.json`, using the lock fragments generated with the ZIPs:

```sh
python tools/pin_release.py /path/to/consumer dist/lock-windows-x64.json dist/lock-linux-x64.json
```

The bootstrap API is `resolve(project, override=None, install=True, archive=None)`.
It returns a tool directory, ready for `python <tool>/mockshadow.py mock`.
The CLI accepts `--project`, `--check` (no downloads/writes), `--archive` (offline
ZIP, still checked against the lock), and `--local` (explicit development path).
Use `identity(tool)` for provenance instead of requiring a Git checkout.

Resolution: explicit override / MOCKSHADOW_ROOT first; otherwise the pinned
package in the consumer's ignored `.tools` directory. It never scans neighboring
repositories, picks `latest`, installs compilers or changes the system PATH.
An explicit broken override fails rather than silently selecting another tool.
Keep existing developer overrides when migrating a project.

Each project has its own cache, allowing different versions. Downloads require
HTTPS and a pinned SHA-256, are staged, and are published by rename only after
verification. Concurrent installations fail with a clear lock message. An
interrupted installer can leave `.tools/.mockshadow-install.lock`; remove it
only after confirming no installer is running. Corrupted installations fail;
remove only the reported package directory and rerun setup to restore it.
No automatic cleanup of other versions occurs. Once installed, reuse is offline.
Hash checks detect corruption, not a compromise of the trusted consumer lock.

## Build and release

1. Commit extractor changes and update the Mockshadow submodule pointer.
2. Set `distribution.VERSION`, commit all tool changes, and build the extractor.
3. Package on each target platform. `tools/package_release.py --help` lists
   extractor, Clang, runtime and license paths. Clean source trees are required;
   `--allow-dirty` is only for local experiments and records the dirty state.
4. Run `tools/smoke_package.py ZIP LOCK` on a clean runtime machine. It checks
   offline install, concurrent extraction, generation/audit/cache and unchanged
   source/tool files. Windows smoke removes developer tools from PATH. This is
   not a VM-level proof of independence; the release workflow adds a fresh runner.
5. Publish the exact ZIP bytes to GitHub Releases at the generated URLs. Never
   overwrite a released version with a different build; use a new version.
6. Update consumer locks from the tested artifacts (both platforms), and keep
   vendored bootstrap copies synchronized. Publish producers before consumers.

The `portable-packages` workflow runs on the distribution feature branch and
manual dispatch. It builds both platforms and runs Windows
acceptance on a separate runner without the build toolchain. It uploads artifacts
and lock fragments. Manual dispatch with `publish=true` publishes a new release
only after both runtime jobs pass. Default builds do not publish or change consumer locks.
Use the exact artifacts for publication; rebuilding changes the checksums.
Source identities in distribution.json describe the build inputs; its file hashes
also cover the runtime DLLs and headers. Consumers include this manifest in their
generation fingerprint. Run `mock --force` after changing external toolchain
dependencies in source mode.

## First implementation status

Local Windows packaging and tests can be run before publication. Until v2.1.0
assets are published, a new consumer must use `--archive` with the prepared ZIP
or select a local checkout. A lock must not advertise a platform that has not
produced a tested artifact. Linux validation/release availability is independent
of Windows; the bootstrap explains missing platforms rather than building them
implicitly. No macOS/ARM package is provided in this iteration.
