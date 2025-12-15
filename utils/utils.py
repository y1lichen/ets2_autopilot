import os
import re
from typing import Union
import sys
import subprocess

if sys.platform == "darwin":
    import AppKit



def has_accessibility_permission():
    if sys.platform != "darwin":
        return
    script = 'tell application "System Events" to return UI elements enabled'
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return result.stdout.strip().lower() == "true"


def request_accessibility_permission():
    if sys.platform != "darwin":
        return
    alert = AppKit.NSAlert.alloc().init()
    alert.setMessageText_("Enable Accessibility Permissions")
    alert.setInformativeText_(
        "This application requires accessibility permissions to function properly. Please enable it in 'System Preferences → Privacy & Security → Accessibility'."
    )
    alert.addButtonWithTitle_("Open Settings")
    alert.addButtonWithTitle_("Cancel")

    response = alert.runModal()

    if response == 1000:  # First button (Open Settings)
        subprocess.run(
            [
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
            ]
        )


def ms_to_kmh(ms: Union[int, float]) -> float:
    """Converts meters per second to kilometers per hour.
    Args:
        ms: Speed in meters per second (int or float).
    Returns:
        Speed in kilometers per hour.
    """
    return ms * 3.6  # Simplified calculation (3600/1000 = 3.6)


def kmh_to_ms(km: Union[int, float]) -> float:
    """Converts kilometers per hour to meters per second.
    Args:
        km: Speed in kilometers per hour (can be an int or a float).
    Returns:
        Speed in meters per second.
    """
    return km / 3.6