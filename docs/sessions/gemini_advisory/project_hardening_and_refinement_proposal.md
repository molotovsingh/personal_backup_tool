# Proposal: Project Hardening and Refinement

This document provides a comprehensive analysis of the project, outlining its strengths, identifying risks, and proposing a prioritized list of actions to improve its correctness, security, and maintainability.

## 1. Executive Summary

The application has a solid foundation with clear architectural layering (models, core, engines, services, routes). The migration from Streamlit to Flask is mostly complete in code, but this has introduced inconsistencies in dependencies, documentation, and configuration.

**The most critical risks are:**

1.  **A mismatch in data/log paths** between the Flask configuration and the core engine logic, which will cause incorrect behavior (e.g., the logs page will not work).
2.  **Several security vulnerabilities** (missing CSRF, permissive CORS, weak secrets) that must be addressed before any production deployment.
3.  **Outdated documentation and dependency files** that do not reflect the current Flask-based application, preventing a clean setup and deployment.

## 2. Strengths

*   **Well-Architected Engines**: The `rsync` and `rclone` engines are well-encapsulated with robust parsing, retry logic, and safety features.
*   **Reliable Storage**: The YAML storage layer uses atomic writes, and the `JobManager` throttles progress updates to prevent excessive I/O.
*   **Modern Frontend**: The Flask app uses modern best practices, including Blueprints for organization, HTMX for dynamic partials, and Socket.IO for real-time updates.
*   **Targeted Tests**: The existing tests for progress parsing and deletion utilities are accurate and provide a good foundation for further testing.

## 3. High-Priority Issues

### 3.1. Data and Log Path Mismatch (Correctness Issue)

There is a critical disagreement between where the Flask app *thinks* data is and where the core engines *actually* write it.

*   **Core Logic (writes to `~/backup-manager/`)**:
    *   `storage/job_storage.py:23`
    *   `core/settings.py:31`
    *   `engines/rsync_engine.py:47`
    *   `engines/rclone_engine.py:66`
*   **Flask App (reads from `./`)**:
    *   `flask_app/config.py:26`
    *   `flask_app/routes/logs.py:83`

**Recommendation**: Unify the data root. The best approach is to use a single environment variable (e.g., `BACKUP_MANAGER_DATA_DIR`) that defaults to `~/backup-manager`. This variable should be used by both the Flask configuration and the core storage/engine modules to ensure they are looking in the same place.

### 3.2. Security and Production Hardening

*   **Missing CSRF Protection**: Mutating requests (e.g., creating or deleting a job) lack CSRF protection. **Action**: Integrate `Flask-WTF` and include CSRF tokens in all forms and HTMX POST/DELETE requests.
*   **Overly Permissive CORS**: `cors_allowed_origins="*"` in `flask_app/__init__.py:24` allows connections from any origin. **Action**: Restrict this to the specific origin(s) that will host the UI.
*   **Weak Default Secret Key**: The default secret in `flask_app/config.py:14` is insecure. **Action**: The application should fail to start in production if `SECRET_KEY` is not set via an environment variable. Additionally, set secure cookie flags: `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_SAMESITE='Lax'`, and `SESSION_COOKIE_HTTPONLY=True`.
*   **Insecure CDN Assets**: The scripts in `flask_app/templates/base.html` are loaded from a CDN without version pinning or Subresource Integrity (SRI) hashes. **Action**: Pin the asset versions and add SRI hashes, or self-host the assets for production.
*   **Debug Logging**: Debug logging for Socket.IO is enabled in `flask_app/__init__.py:26-27`. **Action**: This should be disabled in non-development environments.

### 3.3. Requirements and Documentation Drift

*   **Incorrect Dependencies**: `requirements.txt` still lists Streamlit, not the required Flask stack.
*   **Outdated Instructions**: `README.md` and `install.sh` instruct users to run the old Streamlit app.

**Action**: Update `requirements.txt` with the correct Flask dependencies. Update the `README.md` and any other setup scripts to reflect the new `flask run` command and the current project structure.

## 4. Medium-Priority Issues

*   **Rsync Progress Display**: The UI shows "/ 0 MB" for `rsync` jobs because `total_bytes` is never calculated in `engines/rsync_engine.py:392`. **Action**: Estimate `total_bytes` based on the percentage complete (e.g., `total_bytes = int(bytes_transferred * 100 / percent)`).
*   **Rclone Version Label**: The settings page mislabels the `rclone` path as the version. **Action**: In `flask_app/routes/settings.py:17`, either display the path correctly or parse the output of `rclone --version` to get the actual version string.
*   **Session Directory**: The `flask_sessions/` directory may not exist on startup. **Action**: Ensure this directory is created on startup or use a more robust session management solution.

## 5. Recommendations

I will address these issues in order of priority, starting with the high-priority items. My immediate plan is as follows:

1.  **Unify the Data Root**: Fix the data/log path mismatch to ensure the application functions correctly.
2.  **Harden Security**: Implement the recommended security fixes, starting with CSRF protection and restricting CORS.
3.  **Update Dependencies and Docs**: Correct the `requirements.txt` and `README.md` files to allow for a smooth setup process.

Once these critical issues are resolved, I will proceed with the medium and low-priority items to further improve the application.
