# Proposal: Harden Production Quality and UX Polish

## Why
The Flask migration and security hardening are complete, but several quality-of-life and production-readiness issues remain from the Gemini security audit. These issues affect user experience (rsync progress display, rclone version display), security posture (CDN asset integrity), and code quality (thread safety). Addressing them will complete the production-readiness checklist and ensure a polished, secure application.

## What Changes
- **CDN asset integrity**: Pin CDN library versions and add Subresource Integrity (SRI) hashes to prevent tampering with Tailwind CSS, HTMX, and Socket.IO libraries
- **Rsync progress accuracy**: Fix rsync progress parser to calculate and display total bytes, showing "X MB / Y MB" instead of "X MB / 0 MB"
- **Rclone version display**: Extract actual rclone version string instead of showing the rclone binary path in settings page
- **Thread-safe job iteration**: Add proper locking for job list iteration in JobManager to prevent race conditions during concurrent access

## Impact
- **Affected specs**: 4 capabilities (cdn-integrity, rsync-progress-display, rclone-version-display, job-manager-thread-safety)
- **Affected code**:
  - `flask_app/templates/base.html`: Add SRI hashes to CDN script/link tags
  - `engines/rsync_engine.py`: Parse total file size from rsync output for progress calculation
  - `flask_app/routes/settings.py`: Extract version from rclone binary
  - `core/job_manager.py`: Add threading.Lock for safe job list iteration
- **User-facing improvements**:
  - Better progress accuracy for rsync backups
  - Clearer system information in settings
  - Tamper-proof CDN assets
- **No breaking changes**: All changes are backwards compatible
- **Production readiness**: Completes remaining items from security audit

## Dependencies
- None - all changes are independent and can be implemented in any order
