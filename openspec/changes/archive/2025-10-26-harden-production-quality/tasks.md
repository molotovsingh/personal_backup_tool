# Tasks: Harden Production Quality

## CDN Integrity Protection

- [ ] **Generate SRI hashes for CDN assets**
  - Download current versions of Tailwind CSS (3.4.1), HTMX (1.9.10), Socket.IO (4.6.0)
  - Generate SHA-384 hashes using: `curl -s URL | openssl dgst -sha384 -binary | openssl base64 -A`
  - Document hashes in comments for future reference
  - *Validation*: Hashes generated and documented

- [ ] **Update base.html with pinned versions and SRI**
  - Replace Tailwind CDN URL with: `https://cdn.tailwindcss.com@3.4.1`
  - Add `integrity="sha384-..."` attribute to Tailwind script tag
  - Add `crossorigin="anonymous"` attribute
  - Repeat for HTMX (already version-pinned, add integrity)
  - Repeat for Socket.IO (already version-pinned, add integrity)
  - *Validation*: All three scripts have integrity hashes
  - *Test*: `grep -c 'integrity=' flask_app/templates/base.html` returns 3

- [ ] **Test CDN asset loading**
  - Start Flask app: `uv run python flask_app.py`
  - Open browser to http://localhost:5001
  - Open browser DevTools console
  - Check for SRI-related errors (should be none)
  - Verify Tailwind styling applies correctly
  - Verify HTMX functionality works (create job form)
  - Verify WebSocket connection works
  - *Validation*: All CDN assets load successfully without integrity errors

## Rsync Progress Display Accuracy

- [ ] **Analyze rsync output format**
  - Run sample rsync with --info=progress2: `rsync -av --info=progress2 /test/src /test/dest`
  - Document output format (bytes transferred, percent, speed, time)
  - Identify fields needed for total_bytes calculation
  - *Validation*: Format documented in code comments

- [ ] **Update rsync progress parser**
  - Edit `engines/rsync_engine.py`, locate `_parse_progress_line` method
  - Extract bytes_transferred and percent from rsync output
  - Calculate total_bytes: `int(bytes_transferred / (percent / 100))` when percent > 0
  - Store total_bytes in progress dict (persist once calculated)
  - Handle edge case: percent = 0 (skip total_bytes calculation)
  - *Validation*: Parser returns dict with bytes_transferred, percent, total_bytes keys
  - *Test*: `assert progress['total_bytes'] == int(progress['bytes_transferred'] / (progress['percent'] / 100.0))`

- [ ] **Update job progress update logic**
  - In `_parse_progress_line`, preserve existing total_bytes if already set
  - Only recalculate total_bytes if not set or if new calculation is more accurate
  - Prevent total_bytes from changing once established (avoid UI flicker)
  - *Validation*: total_bytes remains constant after first calculation
  - *Test*: Create rsync job, monitor progress updates, verify total_bytes doesn't change

- [ ] **Test rsync progress display**
  - Create test rsync job with ~100MB of data
  - Start job and watch progress in UI
  - Verify progress shows "X MB / Y MB" instead of "X MB / 0 MB"
  - Verify percentage matches calculated value
  - Verify progress bar fills correctly
  - *Validation*: UI shows accurate total bytes throughout transfer

## Rclone Version Display

- [ ] **Create rclone version helper function**
  - Create new function `get_rclone_version()` in `utils/rclone_helper.py`
  - Execute `subprocess.run(['rclone', 'version'], capture_output=True, text=True)`
  - Parse first line of output to extract version string (format: "rclone v1.65.0")
  - Extract just the version part: `re.search(r'v\d+\.\d+\.\d+', output).group()`
  - Handle FileNotFoundError → return "Not installed"
  - Handle subprocess errors → return "Error detecting version"
  - *Validation*: Function returns semantic version string or error message
  - *Test*: `assert re.match(r'v\d+\.\d+', get_rclone_version())`

- [ ] **Add version caching**
  - Add module-level variable: `_rclone_version_cache = None`
  - In `get_rclone_version()`, check cache first
  - If cache is None, execute version check and cache result
  - Return cached value on subsequent calls
  - *Validation*: Version check executes only once per app lifetime
  - *Test*: Mock subprocess.run, call function twice, verify subprocess called once

- [ ] **Update settings route**
  - Edit `flask_app/routes/settings.py`
  - Import `get_rclone_version` from utils.rclone_helper
  - Replace `info['rclone']['version'] = rclone_path` with `info['rclone']['version'] = get_rclone_version()`
  - Keep `info['rclone']['path'] = rclone_path` separate
  - *Validation*: Settings dict contains both 'version' and 'path' keys
  - *Test*: `assert info['rclone']['version'].startswith('v')`

- [ ] **Test rclone version display**
  - Start Flask app
  - Navigate to Settings page
  - Verify "Rclone Version:" shows semantic version (e.g., "v1.65.0")
  - Verify path is shown separately if needed
  - Test with rclone not installed → shows "Not installed"
  - *Validation*: Version displays correctly in UI

## Job Manager Thread Safety

- [ ] **Add threading lock to JobManager**
  - Import `threading` at top of `core/job_manager.py`
  - Add `self._lock = threading.Lock()` in `__init__` method
  - *Validation*: Lock instance created
  - *Test*: `assert hasattr(manager, '_lock')`

- [ ] **Protect list_jobs with lock**
  - Wrap `list_jobs()` method body with `with self._lock:`
  - Ensure lock is acquired before accessing self.jobs
  - Lock automatically released after method returns
  - *Validation*: list_jobs uses lock context manager
  - *Test*: Run concurrent list_jobs calls, no errors

- [ ] **Protect get_job with lock**
  - Wrap `get_job(job_id)` method body with `with self._lock:`
  - *Validation*: get_job uses lock
  - *Test*: Concurrent reads don't cause errors

- [ ] **Protect create_job with lock**
  - Wrap `create_job()` method body with `with self._lock:`
  - Ensure both in-memory update and storage save are atomic
  - *Validation*: create_job uses lock
  - *Test*: Concurrent creates don't corrupt job list

- [ ] **Protect update_job_progress with lock**
  - Wrap `update_job_progress()` method body with `with self._lock:`
  - *Validation*: update_job_progress uses lock
  - *Test*: Concurrent updates to same job don't lose data

- [ ] **Protect delete_job with lock**
  - Wrap `delete_job()` method body with `with self._lock:`
  - *Validation*: delete_job uses lock
  - *Test*: Concurrent delete and read don't cause iteration errors

- [ ] **Add lock to iteration-based methods**
  - Identify methods that iterate over self.jobs (e.g., _cleanup_completed_jobs)
  - Wrap iterations with `with self._lock:`
  - *Validation*: All iteration-based methods use lock
  - *Test*: Concurrent cleanup and iteration don't raise "dictionary changed size" errors

- [ ] **Write thread safety tests**
  - Create `tests/test_job_manager_thread_safety.py`
  - Test concurrent list_jobs calls (10 threads, 100 iterations each)
  - Test concurrent updates to same job (5 threads updating progress)
  - Test concurrent read during delete (reader and deleter threads)
  - Test concurrent create operations (10 threads creating jobs)
  - *Validation*: All tests pass without race condition errors
  - *Test*: `pytest tests/test_job_manager_thread_safety.py -v`

## Final Validation

- [ ] **Run OpenSpec validation**
  - Execute: `openspec validate harden-production-quality --strict`
  - Resolve any validation errors
  - *Validation*: Validation passes with no errors

- [ ] **Run full test suite**
  - Execute: `pytest tests/ -v`
  - Ensure all existing tests still pass
  - Ensure new thread safety tests pass
  - *Validation*: All tests pass

- [ ] **Manual end-to-end test**
  - Start Flask app: `uv run python flask_app.py`
  - Create rsync backup job
  - Start job and verify progress shows "X MB / Y MB"
  - Navigate to Settings, verify rclone version shows correctly
  - Open browser DevTools, verify no CDN integrity errors
  - Create, update, delete multiple jobs rapidly
  - *Validation*: All features work correctly

- [ ] **Commit changes**
  - Stage all changes: `git add -A`
  - Commit with message: "feat(quality): harden production quality (CDN SRI, rsync progress, rclone version, thread safety)"
  - *Validation*: Changes committed to git
