# main.py
# entry point for the program

import ctypes
from datetime import datetime
from os.path import join
from sys import platform
import time

import cv2
import mss
import numpy as np


# Platform-specific imports
if platform == "win32":
    from win32gui import (
        FindWindow,
        GetForegroundWindow,
        GetWindowRect,
    )
elif platform == "darwin":
    # macOS implementation using PyObjC
    try:
        from Cocoa import NSWorkspace, NSScreen
        from AppKit import NSApplication
    except ImportError:
        print("PyObjC is not installed. Install it with: pip install PyObjC")
        raise

from ets2_imgproc import infer_polyline, CROP_X, CROP_Y, WIN_HEIGHT, WIN_WIDTH
from telemetry.shared_memory_truck_telemetry import SharedMemoryTruckTelemetry
from ets2_telemetry import TelemetryReader
from ets2_telemetry.all_values import AllValues
import ets2_autopilot.calc_input as calc_input
from ets2_autopilot.send_input import send_input

OUTPUT = r"tests\data"


# Platform-specific helper functions
def get_ets2_window_handle():
    """Find the ETS2 window handle (Windows or macOS)"""
    if platform == "win32":
        return FindWindow(None, "Euro Truck Simulator 2")
    elif platform == "darwin":
        return find_ets2_window_macos()
    return None


def find_ets2_window_macos():
    """Find ETS2 window on macOS using NSWorkspace"""
    workspace = NSWorkspace.sharedWorkspace()
    running_apps = workspace.runningApplications()
    
    for app in running_apps:
        if "Euro Truck Simulator 2" in app.localizedName() or "eurotrucks2" in app.bundleIdentifier().lower():
            return app
    return None


def get_window_rect(window_handle):
    """Get window rectangle based on platform"""
    if platform == "win32":
        return GetWindowRect(window_handle)
    elif platform == "darwin":
        return get_window_rect_macos(window_handle)
    return None


def get_window_rect_macos(app):
    """Get window rectangle on macOS"""
    if app is None:
        return None
    
    try:
        # Get the main window of the application
        windows = app.windows() if hasattr(app, 'windows') else []
        if not windows:
            return None
        
        window = windows[0]
        frame = window.frame()
        # Return in format: (x, y, x+width, y+height)
        return (
            int(frame.origin.x),
            int(frame.origin.y),
            int(frame.origin.x + frame.size.width),
            int(frame.origin.y + frame.size.height),
        )
    except Exception as e:
        print(f"Error getting window rect on macOS: {e}")
        return None


def is_window_focused(window_handle):
    """Check if window is focused (Windows or macOS)"""
    if platform == "win32":
        try:
            return GetForegroundWindow() == window_handle
        except:
            return False
    elif platform == "darwin":
        return is_window_focused_macos(window_handle)
    return False


def is_window_focused_macos(app):
    """Check if app is focused on macOS"""
    if app is None:
        return False
    try:
        return app.isActive()
    except:
        return False


def main():
    if platform == "win32":
        try:
            errorCode = ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception as e:
            print(f"Warning: Could not set DPI awareness: {e}")

    global im_src
    telemetry = TelemetryReader()
    all_values = AllValues()
    window_handle = get_ets2_window_handle()

    with mss.mss() as sct:
        last_time = time.perf_counter_ns()
        while True:
            if telemetry is None:
                try:
                    telemetry = SharedMemoryTruckTelemetry()
                except FileNotFoundError:
                    print("\rConnect to the game failed, the plugin file not found, waiting for the game to run.", end="")
                    time.sleep(1)
                    continue
                except Exception as e:
                    print(f"\rUnable to init shared memory{e}")
                    time.sleep(1)
                    continue
            # grab window position
            # assuming you're using Win10 + ETS2 in 1920x1080 window
            if window_handle is None or (platform == "win32" and window_handle == 0):
                print("ETS2 not found, waiting...")
                time.sleep(1)
                window_handle = get_ets2_window_handle()
                continue
            
            # Get window rectangle based on platform
            window_rect = get_window_rect(window_handle)
            if window_rect is None:
                print("Could not get window rect, retrying...")
                time.sleep(1)
                window_handle = get_ets2_window_handle()
                continue
            
            # Build the mss.mss grab area
            if platform == "win32":
                # Windows: window_rect is (x1, y1, x2, y2)
                ets2_window = {
                    "top": window_rect[1] + CROP_Y,
                    "left": window_rect[0] + CROP_X + 10,  # no clue why +10
                    "width": WIN_WIDTH - CROP_X,
                    "height": WIN_HEIGHT - CROP_Y,
                }
            else:
                # macOS: window_rect is also (x1, y1, x2, y2)
                ets2_window = {
                    "top": int(window_rect[1]) + CROP_Y,
                    "left": int(window_rect[0]) + CROP_X + 10,
                    "width": WIN_WIDTH - CROP_X,
                    "height": WIN_HEIGHT - CROP_Y,
                }
            
            # sct.grab is synced to refresh rate,
            # limiting the loop to 60fps or 30fps (if it misses a frame)
            im_src = np.array(sct.grab(ets2_window))
            # magic happens here
            centreline, _ = infer_polyline(im_src)
            
            try:
                telemetry.update()
                if telemetry.is_paused:
                    continue
            except FileNotFoundError:
                print("\rETS2 end or shared memory disconnected", end="")
                telemetry = None  # 重置，重新初始化
                time.sleep(1)
            except Exception as e:
                print(f"\rUnexpected error：{e}")
                time.sleep(1)

            if len(centreline) > 0:
                dt = time.perf_counter_ns() - last_time
                steering = calc_input.CalcInput.pure_pursuit_control_car(
                    all_values, centreline, 10
                )
                # only send input if ETS2 is in focus and unpaused
                # TODO: need to figure out some toggle to enable/disable input
                if (
                    is_window_focused(window_handle)
                    and all_values.general_info.paused == False
                ):
                    send_input(all_values, steering, 0)
            elapsed = (time.perf_counter_ns() - last_time) / 1_000_000_000
            fps = 1 / elapsed
            print(f"FPS: {round(fps, 2):06.2f}" + "-" * round(fps / 10))
            last_time = time.perf_counter_ns()
            # Press "q" to quit
            if cv2.waitKey(1) & 0xFF == ord("q"):
                cv2.destroyAllWindows()
                break
    # end of loop
    print("Exiting...")


if __name__ == "__main__":
    try:
        main()
    except Exception as inst:  # set a breakpoint here as well
        cv2.waitKey(1)
        name = datetime.now().strftime("crash_%Y-%m-%d_%H-%M-%S.png")
        name = join(OUTPUT, name)
        cv2.imwrite(name, im_src)
        print("Program crashed!")
