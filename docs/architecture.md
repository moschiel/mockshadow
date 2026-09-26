# Generation design and next work

Keep a separate source tree: macros, inline/static code, register expressions and
architecture types need modification before host compilation. ARM ELF/DWARF can
inventory symbols but cannot replace an x86 build. Link wrapping complements
recipes for external functions; it does not handle every transformation.

Implemented: content hashes including config/extractor, verified cached outputs,
staged clean inventory, deleted-input handling, project lock, publication rollback
and recovery, non-destructive audit. Generated code no longer pollutes MOCK_TREE.
Physical copies remain independent. Input changes conservatively invalidate all
recipes, including dependencies on headers modified by another recipe. Unchanged
runs reuse all verified transforms. Finer invalidation needs extractor dependency
data; file-only keys would be incorrect. Copy cost is small compared with Clang.

Deferred: a structured extractor protocol returning all symbols, unique-match
checks, diagnostics and dependency files. Batch only phases with unchanged source
and flags; recompute after edits affecting preprocessing/declarations. Detect
overlaps and compare with sequential output before enabling. The current
first-match, early-exit extractor cannot safely batch by passing multiple flags.

Other follow-ups: isolate extractor scratch files across projects, tokenized flag
lists, explicit mappings for additions with ordinary names, strict opt-in
diagnostics/signature validation. These are not implemented guarantees.

Windows shadow-file opens retry transient locks before executing each write.
Bounded publication retries also cover WinError 5 (directory rename can report
access denied for a temporarily held directory); persistent access failures still
stop generation and preserve the prior shadow.
