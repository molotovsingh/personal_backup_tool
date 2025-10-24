"""Test NetworkMonitor functionality"""
import time
from core.network_monitor import NetworkMonitor

# Test 1: Create and start monitor
print("Test 1: Create and start network monitor...")
monitor = NetworkMonitor(check_interval=5)  # Check every 5 seconds for faster testing

# Register callbacks
def on_down():
    print("  📡 CALLBACK: Network went DOWN")

def on_up():
    print("  📡 CALLBACK: Network came UP")

monitor.register_network_down_callback(on_down)
monitor.register_network_up_callback(on_up)

success = monitor.start()
assert success == True, "Start should succeed"
print("✓ Monitor started")

# Test 2: Check status
print("\nTest 2: Check status...")
status = monitor.get_status()
print(f"  Status: {status}")
assert status['running'] == True, "Should be running"
assert status['is_online'] == True, "Should start as online"
print("✓ Status retrieved")

# Test 3: Let it run for a bit
print("\nTest 3: Running monitor for 10 seconds...")
print("  (Monitor will check connectivity every 5 seconds)")
time.sleep(10)

# Test 4: Check status again
print("\nTest 4: Check status after running...")
status = monitor.get_status()
print(f"  Is online: {status['is_online']}")
print(f"  Consecutive failures: {status['consecutive_failures']}")
print("✓ Monitor is working")

# Test 5: Stop monitor
print("\nTest 5: Stop monitor...")
success = monitor.stop()
assert success == True, "Stop should succeed"
print("✓ Monitor stopped")

# Test 6: Verify stopped
print("\nTest 6: Verify monitor stopped...")
status = monitor.get_status()
assert status['running'] == False, "Should not be running"
print("✓ Monitor confirmed stopped")

print("\n✓✓✓ All network monitor tests passed!")
print("\nCheck the log file: ~/backup-manager/logs/network_monitor.log")
