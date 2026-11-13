# Working on Mockshadow

Introduce this as a source transformer, not an instruction-set emulator. Read
README.md, docs/recipes.md and docs/architecture.md, then the consuming simulator's
AGENTS.md/config. Hardware models belong there, not in this generic tool.

Permanent inputs: recipes under configured mocksDirectory with explicit TARGET/MODE, mapped additional files, config and source
checkout. shadow_output/manifest are disposable. Never edit original firmware or
generated code to fix a simulator. Preserve unknown-IO traps and Latin-1 source
processing. No personal skill or absolute machine path is required.

`pipeline.py` owns inventory, hashes, lock and publication; `mock_utils.py` owns
recipe transformations; `audit.py` checks applicability. The extractor is a
submodule: do not accidentally commit binaries or move its ref. Preserve phase
ordering and sequential semantics. Do not run concurrent extraction on the same
extractor checkout (upstream scratch files are shared).

Inspect Git status/branch/submodules first. Use a feature branch; exclude local
env, identities, caches and output. Run Python tests for pipeline changes and the
demo for extractor changes. Check a real consumer for semantic changes. Report
audit, build, boot and behavior separately, with platform and limitations.

Update these checked-in docs when commands, contracts or verified behavior change.
Keep machine paths and temporary evidence in ignored files. Explain the project
and next concrete build command to a new teammate before assuming prior context.

For adapting firmware, read [.agents/skills/mockshadow-firmware/SKILL.md](.agents/skills/mockshadow-firmware/SKILL.md)
and follow its relative references. Discovery and explicit use from a consumer are
documented in [docs/agents.md](docs/agents.md). Keep one canonical workflow; the
Claude Code entry only redirects to it. Reusable examples must be synthetic and
must not import private consumer code, identifiers, paths, logs or data.
