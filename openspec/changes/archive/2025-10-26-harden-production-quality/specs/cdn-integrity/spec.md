# Spec: CDN Integrity Protection

## Summary
Add Subresource Integrity (SRI) hashes and pinned versions to CDN-loaded assets (Tailwind CSS, HTMX, Socket.IO) to prevent tampering and ensure reproducible builds.

## ADDED Requirements

### Requirement: CDN assets SHALL use pinned versions and SRI hashes
The system SHALL load all CDN assets with specific version pins and Subresource Integrity hashes to detect tampering.

#### Scenario: Tailwind CSS loads with SRI hash
```html
<!-- Given: base.html template is rendered -->
<!-- When: Browser loads the page -->
<!-- Then: Tailwind CSS script tag includes integrity hash -->

<script src="https://cdn.tailwindcss.com@3.4.1"
        integrity="sha384-..."
        crossorigin="anonymous"></script>
```

#### Scenario: HTMX loads with pinned version and SRI
```html
<!-- Given: base.html template is rendered -->
<!-- When: Browser loads the page -->
<!-- Then: HTMX script tag includes specific version and integrity hash -->

<script src="https://unpkg.com/htmx.org@1.9.10"
        integrity="sha384-..."
        crossorigin="anonymous"></script>
```

#### Scenario: Socket.IO client loads with SRI protection
```html
<!-- Given: base.html template is rendered -->
<!-- When: Browser loads the page -->
<!-- Then: Socket.IO script tag includes integrity hash -->

<script src="https://cdn.socket.io/4.6.0/socket.io.min.js"
        integrity="sha384-..."
        crossorigin="anonymous"></script>
```

### Requirement: Tampered CDN assets SHALL fail to load
The system SHALL refuse to execute CDN scripts if their integrity hash does not match the expected value.

#### Scenario: Browser detects tampered CDN asset
```python
# Given: Malicious actor modifies Tailwind CSS on CDN
# When: Browser fetches the script and calculates hash
# Then: Hash mismatch detected
# And: Browser refuses to execute the script
# And: Console error logged: "Failed to find a valid digest in the 'integrity' attribute"
# And: Application UI may degrade gracefully but remains functional
```

#### Scenario: CDN responds with correct asset
```python
# Given: CDN serves unmodified Tailwind CSS
# When: Browser fetches the script and calculates hash
# Then: Hash matches integrity attribute
# And: Script executes normally
# And: UI renders with Tailwind styling
```
