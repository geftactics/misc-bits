#!/usr/bin/python3
import plistlib, subprocess

MIN = 20
NAMES = {801: "Magic Keyboard", 803: "Magic Mouse"}

ioreg = subprocess.run(["/usr/sbin/ioreg", "-c", "AppleDeviceManagementHIDEventService", "-r", "-l", "-a"], capture_output=True)

for device in plistlib.loads(ioreg.stdout):
    batt = device.get("BatteryPercent")
    if not isinstance(batt, int):
        continue
    if batt < MIN:
        name = NAMES.get(device.get("ProductID"), device.get("Product") or "Unknown Device")
        subprocess.run(["osascript", "-e", f'display notification "{name} battery is at {batt}%." with title "{name} Battery Low"'])
