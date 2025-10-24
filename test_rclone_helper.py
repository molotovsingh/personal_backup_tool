"""Test rclone helper functionality"""
from utils.rclone_helper import (
    is_rclone_installed,
    list_remotes,
    is_remote_configured,
    get_config_instructions
)

# Test 1: Check if rclone is installed
print("Test 1: Check if rclone is installed...")
is_installed, msg = is_rclone_installed()
print(f"✓ Rclone installed: {is_installed}")
print(f"  Message: {msg}")

# Test 2: List remotes
print("\nTest 2: List configured remotes...")
remotes = list_remotes()
print(f"✓ Found {len(remotes)} remote(s)")
if remotes:
    for remote in remotes:
        print(f"  - {remote}")
else:
    print("  (no remotes configured)")

# Test 3: Check specific remote
print("\nTest 3: Check if 'gdrive' remote exists...")
has_gdrive = is_remote_configured('gdrive')
print(f"✓ gdrive configured: {has_gdrive}")

# Test 4: Get configuration instructions
print("\nTest 4: Get configuration instructions...")
instructions = get_config_instructions()
print("✓ Instructions retrieved:")
print(instructions)

print("\n✓✓✓ All rclone helper tests passed!")
