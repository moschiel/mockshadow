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
package in the shared user installation. Windows uses `%LOCALAPPDATA%/Mockshadow`;
Linux uses `$XDG_DATA_HOME/mockshadow` (default `~/.local/share/mockshadow`).
`MOCKSHADOW_HOME` can explicitly select another shared location. Packages are keyed
by version, platform and archive hash under `packages/`: projects with the same
lock reuse one installation, while different pinned releases coexist.

Run `python setup_mockshadow.py --install-command` in a consumer to install the
small `mockshadow` dispatcher in the shared `bin/` directory. On Windows this adds
only that directory to the user PATH; reopen the terminal. On Linux add it to PATH.
Run `mockshadow mock`, `mockshadow audit` or `mockshadow --version` from a consumer;
the dispatcher finds its nearest ancestor mockshadow.lock.json and uses that pin.
There is no implicit global latest version. Explicit development overrides remain
supported and existing project .env files are preserved.

Downloads require HTTPS and a pinned SHA-256, are staged, and are published by
rename only after verification. Concurrent installers for the same package wait
up to 120 seconds and reuse the first completed installation. Other versions have
independent locks. After interruption, remove a reported lock only after confirming
no installer is running. Corrupted installations fail rather than being used.
Once installed, reuse is offline. No automatic deletion of shared versions occurs.
Hash checks detect corruption, not a compromise of the trusted consumer lock.

For existing local .tools copies, run `python tools/migrate_shared.py --project PATH`
(repeat --project for each consumer). It reuses a verified existing package, checks
that every selected consumer resolves, installs the command, then removes verified
project-local package copies. It leaves unrelated files and explicit source checkouts
alone. Run this from your normal user terminal, not an app-isolated environment.

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

## Published runtime

Version 2.1.0 is published for Windows x64 and Ubuntu 24.04 x64. The shared
installer is consumer-side tooling: it reuses the exact immutable 2.1.0 archives
without republishing or rebuilding them. No macOS/ARM package is provided.
