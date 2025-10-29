# Advisory — Rclone Workflow Hardening

Summary

- The rclone engine is robust for transfers, progress, and retries, but several gaps can affect correctness and operability: per-file deletion retries always fall back to copy, verify-after mode isn’t honored, remote deletions can leave empty directories, preflight checks are missing, and logs are written to a different path than the Flask UI reads.
- This advisory documents issues, impact, and proposes low‑risk, targeted fixes with code references.

Key Issues

1) Per-file deletion retries use copy instead of move
- Problem: When `deletion_mode == 'per_file'`, initial start uses `rclone move` (correct), but `_restart_process()` always builds `rclone copy`.
- Impact: On network errors, subsequent attempts won’t continue per-file deletion semantics; sources may not be emptied as expected.
- Evidence: engines/rclone_engine.py:332 (uses `copy` unconditionally).
- Recommendation: In `_restart_process()`, choose `operation = 'move'` when `delete_source_after` and `deletion_mode == 'per_file'`. Ensure `--delete-empty-src-dirs` is added for move.

2) `verification_mode == 'verify_after'` not honored
- Problem: Settings expose ‘fast’, ‘checksum’, and ‘verify_after’, but only ‘checksum’ affects transfer flags, and post‑transfer verification runs only when deletion mode is verify_then_delete.
- Impact: Users selecting verify_after get no verification unless deletion is also enabled.
- Evidence: core/settings.py:18; engines/rclone_engine.py:455 (verification invoked only under deletion verify-then-delete path).
- Recommendation: On successful transfers, if `verification_mode == 'verify_after'`, run `_verify_backup()` and populate `progress['verification']` fields even when deletion is disabled.

3) Missing preflight for rclone binary
- Problem: No explicit check that rclone is installed and accessible before starting the engine.
- Impact: Failures surface as generic engine start errors, poor UX.
- Evidence: core/job_manager.py:147 (no preflight check); utils/rclone_helper.py:12 (available helper).
- Recommendation: Before constructing RcloneEngine, call `is_rclone_installed()`; if missing, return a clear message to the caller/UI.

4) Remote source cleanup leaves empty directories
- Problem: For remote sources in verify-then-delete, we invoke `rclone delete` but do not remove empty directories.
- Impact: Source remotes accumulate empty directory trees.
- Evidence: engines/rclone_engine.py:520 (remote delete), engines/rclone_engine.py:611 (skips remote cleanup).
- Recommendation: After successful remote delete, invoke `rclone rmdirs <source>` to remove empty directories.

5) Logs path mismatch with Flask Logs page
- Problem: Rclone (and rsync) engines log under `~/backup-manager/logs`, while the Flask UI reads `flask_app/config.py:LOGS_DIR` (repo `logs/`).
- Impact: UI doesn’t display rclone logs created by engines.
- Evidence: engines/rclone_engine.py:66; flask_app/config.py:28; flask_app/routes/logs.py:83.
- Recommendation: Unify data root via a single env‑configurable directory (e.g., `BACKUP_MANAGER_DATA_DIR`) used by engines, storage, settings, and Flask config so logs appear in the UI.

Additional Improvements (Nice-to-have)

- Expand network error pattern list (e.g., “dial tcp”, “connection reset by peer”) and consider checking a larger stderr window for matching.
- Consider `--fast-list` for `rclone delete` on very large trees (trade‑off: memory).
- Expose and document performance trade‑offs when `--checksum` is enabled (slower but safer).

Proposed Changes (Low Risk)

- engines/rclone_engine.py
  - In `_restart_process()`, set `operation = 'move'` when `delete_source_after and deletion_mode == 'per_file'` and add `--delete-empty-src-dirs` similarly to `start()`. Reference: engines/rclone_engine.py:332.
  - After successful transfers, if `verification_mode == 'verify_after'`, call `_verify_backup()` and update `progress['verification']` (passed, files_checked, mismatches). Reference: engines/rclone_engine.py:455.
  - After successful remote delete (`rclone delete`), run `rclone rmdirs <source>` and log outcome. Reference: engines/rclone_engine.py:520.
- core/job_manager.py
  - Before initializing `RcloneEngine`, validate `is_rclone_installed()` and return descriptive error if not. Reference: core/job_manager.py:147; utils/rclone_helper.py:12.
- flask_app/config.py and core/storage/engines
  - Introduce `BACKUP_MANAGER_DATA_DIR` env var; derive logs/jobs/settings paths from it for both Flask UI and engines to eliminate path divergence.

Impact and Risk

- Per-file retry fix aligns retries with the original operation; low risk, improves correctness.
- Verify-after adds optional verification; performance impact limited to runs where enabled.
- Remote rmdirs prevents clutter on remotes; safe after deletion completes.
- Preflight check improves UX by providing actionable errors early.
- Data path unification is operational plumbing; requires careful rollout to avoid splitting data locations. Mitigate by defaulting to the current home‑dir path and allowing override via env.

Testing Plan

1) Per-file retry
- Simulate a move with induced network error; confirm `_restart_process()` uses `rclone move` and that sources are removed progressively. Inspect logs under the unified data dir.

2) Verify-after
- Set `verification_mode='verify_after'` with deletion disabled; run a small transfer; assert verification runs and `progress['verification']` fields are populated. Inject mismatches to verify failure path.

3) Remote delete and rmdirs
- Use a test remote (or mock subprocess) to confirm `rclone delete` then `rclone rmdirs` are invoked; verify log messages and handle non‑zero return codes gracefully.

4) Preflight rclone
- Temporarily mask rclone from PATH; attempt start and assert a clear “rclone not found” error is returned to the UI.

5) Logs visibility
- After unifying data dir, run a small job; confirm logs appear in the Flask Logs page filter and export view.

File References

- engines/rclone_engine.py:90
- engines/rclone_engine.py:96
- engines/rclone_engine.py:105
- engines/rclone_engine.py:332
- engines/rclone_engine.py:364
- engines/rclone_engine.py:455
- engines/rclone_engine.py:520
- engines/rclone_engine.py:611
- core/job_manager.py:147
- utils/rclone_helper.py:12
- flask_app/config.py:28
- flask_app/routes/logs.py:83

