# send_input.py
# send input to ETS2 via keyboard/mouse inputs
# note: controls.sii in game needs to be changed to:
#  config_lines[0]: "device keyboard `sys.keyboard`"
#  config_lines[1]: "device mouse `sys.mouse`"
from utils.scs_controller import SCSController
from sys import platform
from telemetry.truck_telemetry import TruckTelemetry

# Platform-specific imports
if platform == "win32":
    import pydirectinput
elif platform == "darwin":
    import pyautogui

controller = SCSController()

def send_input(telemetry: TruckTelemetry, steering, throttle):
    """Send steering and throttle input to ETS2.
    
    Works on both Windows and macOS.
    """
    # use relative move to control steering
    # positive to steer right, negative to steer left

    # TODO: fix asap!!
    curr_steering = telemetry.truck_input_steer_value
    steering_error = curr_steering - steering
    # print(f'{curr_steering} > {steering} ?')
    if steering_error > 0.15:
        controller.set_steering(steering_error)
    else:
        controller.set_steering(0.0)
    # steer(steering_error * 400)  # magic number calculated through magic:
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




