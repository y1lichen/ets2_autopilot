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


from ets2_imgproc import infer_polyline, CROP_X, CROP_Y, WIN_HEIGHT, WIN_WIDTH
from telemetry.shared_memory_truck_telemetry import SharedMemoryTruckTelemetry

import ets2_autopilot.calc_input as calc_input
from ets2_autopilot.send_input import send_input

OUTPUT = r"tests/data"


def main():
    global im_src
    telemetry = None
    window_rect = (0, 0, WIN_WIDTH, WIN_HEIGHT)
    
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
            print(len(centreline))
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
                    telemetry, centreline, 10
                )
                # only send input if ETS2 is in focus and unpaused
                # TODO: need to figure out some toggle to enable/disable input
                send_input(telemetry, steering, 0)
            elapsed = (time.perf_counter_ns() - last_time) / 1_000_000_000
            fps = 1 / elapsed
            # print(f"FPS: {round(fps, 2):06.2f}")
            last_time = time.perf_counter_ns()
            # Press "q" to quit
            if cv2.waitKey(1) & 0xFF == ord("q"):
                cv2.destroyAllWindows()
                break
    # end of loop
    print("Exiting...")


if __name__ == "__main__":
    main()
    # try:
    #     main()
    # except Exception as inst:  # set a breakpoint here as well
    #     cv2.waitKey(1)
    #     name = datetime.now().strftime("crash_%Y-%m-%d_%H-%M-%S.png")
    #     name = join(OUTPUT, name)
    #     cv2.imwrite(name, im_src)
    #     print("Program crashed!")
