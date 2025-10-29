# Advisory — Retire Streamlit App

Summary

- The project has completed the migration to Flask with full feature parity and performance improvements (see FLASK_MIGRATION_COMPLETE.md:11). The legacy Streamlit UI (`app.py`) remains present and is referenced in a few developer docs/scripts. This advisory proposes a clear, low‑risk plan to deprecate and retire the Streamlit app. No code changes are included here; this is a planning document for a follow‑up PR.

Decision

- Deprecate the Streamlit UI and make Flask the sole supported UI.
- Recommended timeline: 7‑day deprecation window with in‑app notice, then archive Streamlit.
  - Alternative: Immediate cutover (smaller change surface; suitable for solo/local usage).

Context

- Flask UI is the new default (port 5001) and uses shared business logic. Streamlit continues to exist mainly for historical reasons and is still referenced by some docs/scripts. Removing Streamlit reduces maintenance, avoids user confusion, and prevents divergence between UIs.

Scope (Docs/Process Only)

- This advisory only adds guidance. Implementation should be done in a separate PR.
- No code, dependency, or behavior changes are performed as part of this advisory.

Plan of Record (Two-Phase)

Phase 1 — Deprecation (0–7 days)

1) Communicate deprecation
   - Streamlit banner (optional during window): “The Streamlit UI is deprecated and will be retired on <date>. Use http://localhost:5001.” Add after page config.
     - Reference: app.py:49
   - If banner is skipped, proceed directly to Phase 2 (Immediate Cutover).

2) Update references in docs/scripts (proposed edits in follow‑up PR)
   - install.sh:76 → Replace streamlit start hint with Flask: `uv run python flask_app.py`.
     - Reference: install.sh:76
   - TESTING.md:26, TESTING.md:133 → Replace streamlit start commands with Flask.
     - References: TESTING.md:26, TESTING.md:133
   - setup_jobs.py:169 → Replace printed guidance with Flask start command.
     - Reference: setup_jobs.py:169
   - requirements.txt:18–20 → Remove legacy Streamlit lines (currently commented) during cleanup.
     - Reference: requirements.txt:18
   - README.md already points to Flask; verify no remaining Streamlit start instructions.
     - Reference: README.md:54 (Flask quick start present)

Phase 2 — Retirement (after deprecation window or immediately)

3) Archive Streamlit app
   - Move `app.py` and `app.py.bak` to `archive/streamlit/`.
   - Optionally leave a stub `app.py` that prints a clear message if invoked: “Streamlit UI retired. Run: uv run python flask_app.py”.
   - References: app.py:1, app.py.bak:1

4) Dependency and dev notes cleanup
   - Remove commented Streamlit dependencies from `requirements.txt`.
     - Reference: requirements.txt:18
   - Adjust `requirements-dev.txt` comment if it implies Streamlit‑specific hot‑reload; keep or remove `watchdog` based on current dev workflow.
     - Reference: requirements-dev.txt:4

5) Remove residual mentions
   - Search and update any remaining references:
     - Command: `rg -n "streamlit|streamlit run|st\." -S`
   - Keep historical mention in FLASK_MIGRATION_COMPLETE.md under the “Running Both Apps” section, or annotate that Streamlit is archived.
     - References: FLASK_MIGRATION_COMPLETE.md:137–144

6) Tag and document
   - Tag the last commit containing the Streamlit UI: `streamlit-ui-final`.
   - Add a brief deprecation note to CHANGELOG or release notes.

Impact and Risk

- User impact: Minimal; Flask replaces Streamlit with better performance and UX. Users launching via old commands will see updated docs or a stub message.
- Operational: Update local scripts or services that call `streamlit run app.py` to `python flask_app.py`.
- Risk: Low. Streamlit and Flask share business logic; retirement primarily removes a duplicate UI.

Rollback Plan

- Keep `archive/streamlit/` folder for quick restoration.
- Revert the doc/script changes and restore `app.py` to root if needed.

Validation Checklist (Post‑Change)

- Launch: `uv run python flask_app.py` serves UI at http://localhost:5001
- Docs: `install.sh`, `TESTING.md`, and `setup_jobs.py` show Flask start command
- Search: `rg` shows no in‑repo guidance to run Streamlit (outside archives and historical docs)
- Jobs and logs function as before via Flask pages

References (Click to open)

- app.py:49
- app.py.bak:1
- install.sh:76
- TESTING.md:26
- TESTING.md:133
- setup_jobs.py:169
- requirements.txt:18
- requirements-dev.txt:4
- FLASK_MIGRATION_COMPLETE.md:137
- FLASK_MIGRATION_COMPLETE.md:138
- FLASK_MIGRATION_COMPLETE.md:144
- README.md:54

Notes

- If you prefer Immediate Cutover, skip Phase 1 banner and proceed directly with Phase 2. For teams/users accustomed to the Streamlit command, consider leaving a stub `app.py` for one release to provide a friendly redirect message.

