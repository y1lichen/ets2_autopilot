# send_input.py
# send input to ETS2 via keyboard/mouse inputs
# note: controls.sii in game needs to be changed to:
#  config_lines[0]: "device keyboard `sys.keyboard`"
#  config_lines[1]: "device mouse `sys.mouse`"

from sys import platform
from ets2_telemetry.all_values import AllValues

# Platform-specific imports
if platform == "win32":
    import pydirectinput
elif platform == "darwin":
    try:
        from CoreGraphics import CGEventCreateMouseEvent, CGEventPost, kCGEventMouseMoved, kCGMouseCursorSet
        from Cocoa import NSEvent
    except ImportError:
        print("PyObjC is not installed. Install it with: pip install PyObjC")
        raise


def send_input(telemetry: AllValues, steering, throttle):
    """Send steering and throttle input to ETS2.
    
    Works on both Windows and macOS.
    """
    # use relative move to control steering
    # positive to steer right, negative to steer left
    """
    if throttle == 1:
        key_up/down("down", _pause=False)
        key_up/down("up", _pause=False)
    elif throttle == -1:
        key_up/down("up", _pause=False)
        key_up/down("down", _pause=False)
    else: # 0 throttle/brake, just coast
        key_up/down("down", _pause=False)
        key_up/down("up", _pause=False)
    """

    # TODO: fix asap!!
    curr_steering = telemetry.user_inputs.steer
    steering_error = curr_steering - steering
    # print(f'{curr_steering} > {steering} ?')
    steer(steering_error * 400)  # magic number calculated through magic:
    # set the magic steer multiplier to 90% of the value below
    # 100 pixels -> 0.0633509 steer at 0.05 sens -> 1579
    # 100 pixels -> 0.2293 steer at 0.40 sens -> 436
    # 100 pixels -> 0.7524 steer at 1.50 sens -> 133
    """
    if curr_steering > steering:
        steer(10)
    else:
        steer(-10)
    """
    return


def steer(movement):
    """Move the mouse by the given amount (relative movement).
    
    Works on both Windows and macOS.
    positive = right, negative = left
    """
    movement = round(movement)
    
    if platform == "win32":
        pydirectinput.move(movement, 0, _pause=False, relative=True)
    elif platform == "darwin":
        steer_macos(movement)
    else:
        print(f"Platform {platform} is not supported for input control")


def steer_macos(movement):
    """Move the mouse on macOS using CoreGraphics.
    
    Args:
        movement: Positive for right, negative for left
    """
    try:
        from CoreGraphics import CGEventCreateMouseEvent, CGEventPost, kCGEventMouseMoved, kCGHIDEventTap
        from Cocoa import NSEvent
        
        # Get current mouse location
        event = NSEvent.mouseLocation()
        current_x = event.x
        current_y = event.y
        
        # Calculate new position
        new_x = current_x + movement
        new_y = current_y
        
        # Create and post the mouse event
        mouse_event = CGEventCreateMouseEvent(
            None,
            kCGEventMouseMoved,
            (new_x, new_y),
            0
        )
        CGEventPost(kCGHIDEventTap, mouse_event)
    except Exception as e:
        print(f"Error moving mouse on macOS: {e}")

