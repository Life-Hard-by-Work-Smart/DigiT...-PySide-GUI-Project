"""Test script to trigger point movement and capture logs"""
import time
import sys

# Give app time to load
print("Waiting for app to load...")
time.sleep(5)

print("=" * 80)
print("TEST: SIMULATING ARROW KEY MOVEMENT ON FIRST POINT")
print("=" * 80)

try:
    # Try to use pyautogui to send keyboard events
    import pyautogui

    # Move mouse to center of canvas (approximate - we'll let the GUI handle it)
    # For now, just send arrow key presses
    print("\n>>> Sending Arrow Key: RIGHT")
    pyautogui.press('right')
    time.sleep(0.5)

    print(">>> Sending Arrow Key: UP")
    pyautogui.press('up')
    time.sleep(0.5)

    print(">>> Sending Arrow Key: LEFT (with Shift for 5px)")
    pyautogui.hotkey('shift', 'left')
    time.sleep(0.5)

    print("\n✓ Arrow key tests complete")

except ImportError:
    print("PyAutoGUI not available, skipping automated test")
    print("\nManual test instructions:")
    print("1. Click on any point in the canvas (left side)")
    print("2. Press UP arrow key")
    print("3. Watch console for debug output")
    print("4. Check if table coordinates updated")

print("\n" + "=" * 80)
print("Check the console output above for debug logs")
print("=" * 80)

# Keep the process alive
time.sleep(10)
print("\nTest complete. App still running...")
