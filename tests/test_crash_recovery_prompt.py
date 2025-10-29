"""Test crash recovery prompt rendering."""
import pytest


def test_crash_recovery_prompt_rendered(client):
    """Test crash recovery prompt appears when interrupted jobs exist."""
    with client.session_transaction() as sess:
        sess['interrupted_jobs'] = ['job1', 'job2']
        sess['show_recovery_prompt'] = True
        sess['interrupted_job_count'] = 2
        sess['crash_check_done'] = True  # Skip crash check, use our values

    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Crash Detected' in html
    assert 'Recover (mark as paused)' in html
    assert 'Dismiss' in html
    assert '2 interrupted job(s)' in html


def test_no_crash_recovery_when_no_interrupted_jobs(client):
    """Test crash recovery prompt does not appear when no interrupted jobs."""
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Crash Detected' not in html
    assert 'Recover (mark as paused)' not in html


def test_crash_recovery_helper_text(client):
    """Test crash recovery prompt includes helper text (Phase 3 enhancement)."""
    with client.session_transaction() as sess:
        sess['interrupted_jobs'] = ['job1']
        sess['show_recovery_prompt'] = True
        sess['interrupted_job_count'] = 1
        sess['crash_check_done'] = True  # Skip crash check, use our values

    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Check for helper text added in Phase 3
    assert 'Ensures safe state; resume later from Jobs.' in html


def test_crash_recovery_buttons_have_onclick(client):
    """Test crash recovery buttons have disable-on-click (Phase 3 enhancement)."""
    with client.session_transaction() as sess:
        sess['interrupted_jobs'] = ['job1']
        sess['show_recovery_prompt'] = True
        sess['interrupted_job_count'] = 1
        sess['crash_check_done'] = True  # Skip crash check, use our values

    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Check for onclick attribute that disables buttons
    assert 'onclick="this.disabled=true; this.form.submit();"' in html
