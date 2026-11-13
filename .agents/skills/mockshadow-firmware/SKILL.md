---
name: mockshadow-firmware
description: Adapt C firmware into a separate native Windows/Linux or WebAssembly simulation using Mockshadow v2 recipes. Use when creating a simulator, replacing hardware boundaries, diagnosing transformations or unmodeled operations, or validating a generated shadow tree while preserving original sources.
---

# Adapt firmware with Mockshadow

Treat Mockshadow as a recipe-driven source transformer. It does not emulate CPU
instructions, supply peripheral models automatically, or guarantee hardware timing.

1. Locate the Mockshadow checkout containing this file (three directories up).
   Resolve links relative to this file, not the shell's working directory. Read
   applicable AGENTS.md files in both checkouts and inspect Git status, branch and
   the extractor submodule. Preserve existing changes; use a work branch.
2. Read the [README](../../../README.md), [recipe contract](../../../docs/recipes.md)
   and [architecture](../../../docs/architecture.md). Run `python mockshadow.py --help`
   from the Mockshadow root; confirm toolchains before promising a build.
3. Follow the [adaptation procedure](../../../docs/firmware-adaptation.md): inventory
   the original build and hardware boundaries, define preserved behavior, and
   choose stubs, stateful models or functional implementations deliberately.
4. Select [native](../../../docs/targets/native.md) or
   [WebAssembly](../../../docs/targets/webassembly.md). Keep application code,
   transformation recipes and simulation models separate. Models and build/runtime
   adapters belong in the consuming simulator, outside its `mocks` directory.
5. Reproduce the [examples](../../../examples/README.md) before adapting unfamiliar
   code. Run extraction, audit and generation sequentially for one extractor
   checkout: its scratch files are shared, even across separate consumers.
6. Work from the consumer root for `list`, `open-mock`, `audit` and `mock`. Correct
   permanent recipes, additions, config and build inputs; never fix a simulation
   by editing the original firmware or `shadow_output`. Preserve explicit errors
   for unsupported operations; do not replace failures with unconditional success.
7. Validate audit, transformation, compilation, initialization and behavior
   separately. Include negative cases and reset/state transitions. Diagnose the
   failing layer before changing code; report possible application bugs separately.
8. Record commands, toolchain/platform, inputs/expected outputs, limitations and
   pending checks in the consumer's docs. Report only platforms actually exercised.

Use original synthetic examples for reusable documentation. Do not import private
consumer code, identifiers, recipes, paths, logs or data into this repository.

For explicit reading, discovery and use from another project, see
[agent integration](../../../docs/agents.md). Keep the full checkout available;
copying this folder alone breaks its documentation links.
