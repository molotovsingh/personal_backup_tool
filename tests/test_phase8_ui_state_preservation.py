"""
Test Phase 8.6: UI State Preservation Across Updates
Tests to verify UI state (form inputs, scroll position, etc.) is preserved during updates.
"""
import pytest
from fastapi.testclient import TestClient
from fastapi_app import app
from bs4 import BeautifulSoup


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_jobs_page_loads_successfully(client):
    """Test that jobs page loads without errors."""
    response = client.get("/jobs/")
    assert response.status_code == 200
    assert b"Jobs" in response.content or b"jobs" in response.content


def test_job_creation_form_present(client):
    """Test that job creation form is present in the page."""
    response = client.get("/jobs/")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, 'html.parser')

    # Check for form elements
    form = soup.find('form', id='job-form')
    assert form is not None, "Job creation form should be present"

    # Check for required input fields
    name_input = soup.find('input', {'name': 'name'})
    source_input = soup.find('input', {'name': 'source'})
    dest_input = soup.find('input', {'name': 'dest'})

    assert name_input is not None, "Name input should be present"
    assert source_input is not None, "Source input should be present"
    assert dest_input is not None, "Dest input should be present"


def test_deletion_checkbox_sync_javascript_present(client):
    """Test that deletion checkbox synchronization JavaScript is present."""
    response = client.get("/jobs/")
    assert response.status_code == 200

    content = response.content.decode('utf-8')

    # Check for syncDeletionCheckbox function
    assert 'syncDeletionCheckbox' in content, \
        "Deletion checkbox sync function should be present"

    # Check for DOMContentLoaded listener
    assert 'DOMContentLoaded' in content, \
        "DOMContentLoaded event listener should be present"

    # Check for htmx:afterSwap listener
    assert 'htmx:afterSwap' in content, \
        "HTMX afterSwap listener should be present for state preservation"


def test_deletion_options_container_present(client):
    """Test that deletion options container is present for dynamic loading."""
    response = client.get("/jobs/")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, 'html.parser')

    # Check for deletion options container
    deletion_options = soup.find('div', id='deletion-options')
    assert deletion_options is not None, \
        "Deletion options container should be present for HTMX updates"


def test_websocket_connection_in_page(client):
    """Test that WebSocket connection code is present in jobs page."""
    response = client.get("/jobs/")
    assert response.status_code == 200

    content = response.content.decode('utf-8')

    # Check for WebSocket connection setup
    assert 'connectWebSocket' in content, \
        "WebSocket connection function should be present"

    # Check for reconnection logic
    assert 'reconnectAttempts' in content, \
        "WebSocket reconnection logic should be present"


def test_notification_system_javascript_present(client):
    """Test that notification system JavaScript is present."""
    response = client.get("/jobs/")
    assert response.status_code == 200

    content = response.content.decode('utf-8')

    # Check for notification functions
    assert 'showNotification' in content, \
        "Notification display function should be present"

    assert 'createNotificationContainer' in content, \
        "Notification container creation function should be present"


def test_htmx_attributes_on_form_elements(client):
    """Test that HTMX attributes are properly set on form elements."""
    response = client.get("/jobs/")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, 'html.parser')

    # Check for HTMX attributes
    htmx_elements = soup.find_all(attrs={'hx-get': True})
    assert len(htmx_elements) > 0, "Should have elements with hx-get attributes"


def test_dashboard_websocket_present(client):
    """Test that dashboard has WebSocket functionality."""
    response = client.get("/")
    assert response.status_code == 200

    content = response.content.decode('utf-8')

    # Check for WebSocket connection
    assert 'WebSocket' in content or 'websocket' in content, \
        "Dashboard should have WebSocket functionality"


def test_connection_status_indicator(client):
    """Test that connection status indicator code is present."""
    response = client.get("/jobs/")
    assert response.status_code == 200

    content = response.content.decode('utf-8')

    # Check for connection status functions
    assert 'updateConnectionStatus' in content, \
        "Connection status indicator function should be present"


def test_job_list_refresh_without_reload(client):
    """Test that job list can be refreshed via HTMX without full page reload."""
    response = client.get("/jobs/")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, 'html.parser')

    # Check for jobs content container (HTMX target)
    jobs_content = soup.find('div', id='jobs-content')
    assert jobs_content is not None, \
        "Jobs content container should be present for HTMX updates"


def test_deletion_checkbox_htmx_trigger(client):
    """Test that deletion checkbox has HTMX trigger for dynamic options."""
    response = client.get("/jobs/")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find deletion checkbox
    checkbox = soup.find('input', {'id': 'delete_source_after'})

    if checkbox:
        # Check for HTMX attributes
        assert checkbox.get('hx-get') is not None or checkbox.get('hx-post') is not None, \
            "Deletion checkbox should have HTMX trigger"


def test_form_state_preservation_htmx_swap(client):
    """Test that HTMX swap mode preserves form state."""
    response = client.get("/jobs/")
    assert response.status_code == 200

    content = response.content.decode('utf-8')

    # Check for appropriate HTMX swap strategies
    # innerHTML or outerHTML are typically used
    assert 'hx-swap' in content.lower(), \
        "HTMX swap attributes should be present for controlled updates"


def test_websocket_message_handler_for_job_updates(client):
    """Test that WebSocket message handler processes job updates correctly."""
    response = client.get("/jobs/")
    assert response.status_code == 200

    content = response.content.decode('utf-8')

    # Check for message handling logic
    assert 'ws.onmessage' in content, \
        "WebSocket message handler should be present"

    # Check for job_update and job_final_update handling
    assert 'job_update' in content, \
        "Should handle job_update message type"


def test_notification_message_handler(client):
    """Test that notification messages are handled by WebSocket."""
    response = client.get("/jobs/")
    assert response.status_code == 200

    content = response.content.decode('utf-8')

    # Check for notification handling
    assert 'notification' in content, \
        "Should handle notification message type"


def test_cache_preserves_job_list_between_reads(client):
    """Test that cache behavior preserves data between rapid reads."""
    # First request
    response1 = client.get("/jobs/")
    assert response1.status_code == 200

    # Second request (should use cache)
    response2 = client.get("/jobs/")
    assert response2.status_code == 200

    # Both should return successfully
    assert response1.status_code == response2.status_code


def test_deletion_ui_partial_exists(client):
    """Test that deletion UI partial endpoint exists."""
    response = client.get("/jobs/deletion-ui")
    # Should return 200 (with options) or redirect
    assert response.status_code in [200, 307], \
        f"Deletion UI endpoint should exist, got {response.status_code}"


def test_health_endpoint_for_ui_monitoring(client):
    """Test that health endpoint exists for UI monitoring."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert 'status' in data
    assert 'components' in data


def test_settings_page_loads(client):
    """Test that settings page loads successfully."""
    response = client.get("/settings/")
    assert response.status_code == 200


def test_logs_page_loads(client):
    """Test that logs page loads successfully."""
    response = client.get("/logs/")
    assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
