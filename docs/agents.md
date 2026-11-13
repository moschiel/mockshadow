# Using Mockshadow with coding agents

The repository contains one workflow in the common Agent Skills format: YAML
`name`/`description` followed by Markdown instructions. No plugin, MCP server,
account installation or personal skill is required.

## Explicit reading: any agent with repository access

Give the agent the checkout location and ask it to read
[.agents/skills/mockshadow-firmware/SKILL.md](../.agents/skills/mockshadow-firmware/SKILL.md).
It must follow the relative documentation links as well. Reading a file explicitly
works even if the client does not discover skills. It does not register a skill
or grant access to another directory.

For example, with sibling `mockshadow`, `firmware` and `simulator` directories,
start the agent in their common workspace and say:

> Read mockshadow/.agents/skills/mockshadow-firmware/SKILL.md and follow its linked
> documentation. Adapt firmware into a separate simulator for native execution.
> Inspect the original build first, reproduce the included stateful example, then
> identify the smallest hardware boundary needed for a useful test. Keep firmware
> unchanged. Record preserved behavior, unsupported operations and validation
> results. Use only permanent simulator inputs for fixes. Do not publish changes.

For a browser target, replace "native execution" with "WebAssembly in a browser"
and specify the required interaction (for example, injecting samples and stepping
virtual time). The agent must check Emscripten and browser availability, rather
than claiming a native test validates the browser.

## Discovery in compatible clients

| Client/context | Repository entry | How to request it |
| --- | --- | --- |
| Codex CLI/IDE with this checkout in its repository discovery scope | `.agents/skills/mockshadow-firmware/SKILL.md` (canonical source) | Select it through `/skills` or mention `$mockshadow-firmware` |
| Claude Code with this checkout in scope | `.claude/skills/mockshadow-firmware/SKILL.md` (thin adapter) | `/mockshadow-firmware` |
| Any client working only in a different consumer checkout | No assumed cross-repository discovery | Ask it to read the canonical file explicitly, granting checkout access if needed |

Automatic selection depends on client version, configuration, enabled skills and
task relevance. Verify it appears in the client's skill list; presence on disk is
not proof of loading. This delivery verifies the files and explicit-reading
workflow, not every client UI. Both entries refer to the same maintained workflow;
there is no generated duplicate or symlink requirement on Windows.

Keep the complete repository layout when moving the checkout. The skill references
the existing docs and examples outside its own directory, so it is a repository
skill, not a standalone folder upload. Do not copy only SKILL.md to a personal
skills directory. Installation and distribution packaging are outside this step.

Format and discovery references (checked 2026-11-12):
[Codex skills](https://learn.chatgpt.com/docs/build-skills) and
[Claude Code skills](https://code.claude.com/docs/en/skills).

## Daily workflow

Keep the original firmware checkout separate from the consuming simulator.
After an original source update, run `audit`, inspect changed boundaries, then
`mock`, compile and exercise scenarios. A matching symbol is not proof of matching
semantics. Save the simulator's models, recipes, build settings and test scenarios
in its own repository. Keep its local environment and generated tree ignored.

Use [the adaptation procedure](firmware-adaptation.md) for the first port and
[the recipe reference](recipes.md) for syntax. Start with the existing battery
demo for a minimal replacement, then the [stateful example](../examples/README.md)
for injected inputs, time, output state and explicit errors.
