<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

## Codex Agent Policy: Advice-Only Mode (Default)

Scope: This section applies to the Codex CLI agent only. Other agents (e.g., Claude) follow their own configs.

Rules (must-follow for Codex):

- Do not modify files unless the user explicitly authorizes changes in this conversation (e.g., "you can modify X" or an approved OpenSpec proposal/tasks.md). Otherwise, provide advice, diffs, or patch plans only.
- Do not call write-capable tools (e.g., `apply_patch`) or run commands that write to disk by default. Use read-only shell actions (e.g., `ls`, `rg`, `cat`).
- Request explicit approval before any action that can write files, alter the environment, install packages, or access the network.
- Do not create commits, branches, or push changes unless the user asks.
- Prefer proposing minimal, surgical patches with clear file paths and rationale. Apply only after authorization.
- For feature work, architecture, or breaking changes, follow `@/openspec/AGENTS.md` and require an approved change proposal before implementation.

Operational guidance (Codex):

- When a write is requested, limit changes strictly to the files and scope specified by the user, and summarize the impact.
- If tests or tools may write to temp or cache directories, ask for approval first and note any side effects.
- Keep network access restricted unless specifically requested.
- Surface any ambiguities with a brief clarifying question before proposing patches.

Suggested local Codex defaults (optional):

- In `~/.codex/config.toml`, set this project as untrusted to require approvals:

```toml
[projects."/Users/aks/backup-manager"]
trust_level = "untrusted"
```

- Alternatively, add a shell alias (does not change other agents):

```sh
alias codex='codex --sandbox read-only --approval untrusted'
```

