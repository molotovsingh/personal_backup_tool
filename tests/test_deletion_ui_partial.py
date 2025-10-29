"""Test deletion UI partial endpoint."""
import pytest


def test_deletion_ui_true(client):
    """Test deletion UI returns content when delete_source_after=true."""
    resp = client.get('/jobs/deletion-ui?delete_source_after=true')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="deletion_confirmed"' in html
    assert 'value="verify_then_delete"' in html
    assert 'Deletion Mode' in html


def test_deletion_ui_false(client):
    """Test deletion UI returns empty when delete_source_after=false."""
    resp = client.get('/jobs/deletion-ui?delete_source_after=false')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="deletion_confirmed"' not in html
    assert 'Deletion Mode' not in html


def test_deletion_ui_missing_param(client):
    """Test deletion UI handles missing parameter gracefully."""
    resp = client.get('/jobs/deletion-ui')
    assert resp.status_code == 200
    # Should default to false (no options shown)
    html = resp.get_data(as_text=True)
    assert 'id="deletion_confirmed"' not in html


def test_deletion_ui_contains_fieldset(client):
    """Test deletion UI uses semantic fieldset for radio group."""
    resp = client.get('/jobs/deletion-ui?delete_source_after=true')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Check for fieldset wrapper (Phase 2 enhancement)
    assert '<fieldset' in html
    assert '<legend' in html


def test_deletion_ui_radio_options(client):
    """Test deletion UI contains both radio options."""
    resp = client.get('/jobs/deletion-ui?delete_source_after=true')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Check for both deletion mode options
    assert 'value="verify_then_delete"' in html
    assert 'value="per_file"' in html
    assert 'Verify Then Delete' in html
    assert 'Per-File Deletion' in html
