import ctypes
from datetime import datetime
from os.path import join
from sys import platform
import time

import cv2
import mss
import numpy as np

# 確保導入正確的常數
from ets2_imgproc import HOMOGRAPHY, TRUCK_CENTRE, WIN_WIDTH, CROP_X, WIN_HEIGHT, CROP_Y, infer_polyline
from telemetry.shared_memory_truck_telemetry import SharedMemoryTruckTelemetry
import ets2_autopilot.calc_input as calc_input
from ets2_autopilot.send_input import send_input
from utils.scs_controller import SCSController

controller = SCSController()

def main():
    global im_src
    telemetry = None
    window_rect = (0, 0, WIN_WIDTH, WIN_HEIGHT)

    # --- 修正影片寫入器設定 ---
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    # 俯視圖轉化後的畫布大小是 (2000, 2000)，錄影機尺寸必須完全一致
    TOP_DOWN_SIZE = (2000, 2000)
    video_out = cv2.VideoWriter(
        'autopilot_output.mp4', 
        fourcc, 
        20.0, # 稍微調低 FPS 減輕寫入壓力
        TOP_DOWN_SIZE
    )
    
    with mss.mss() as sct:
        last_time = time.perf_counter_ns()
        while True:
            # ... (telemetry 初始化代碼保持不變) ...
            if telemetry is None:
                try:
                    telemetry = SharedMemoryTruckTelemetry()
                except:
                    time.sleep(1)
                    continue

            # 抓取畫面
            ets2_window = {
                "top": window_rect[1] + CROP_Y,
                "left": window_rect[0] + CROP_X,
                "width": WIN_WIDTH - CROP_X,
                "height": WIN_HEIGHT - CROP_Y,
            }
            
            sct_img = sct.grab(ets2_window)
            im_src = np.array(sct_img)

            # 影像處理：找出中心線
            centreline, imout, centreline_image = infer_polyline(im_src)

            # 遙測更新
            try:
                telemetry.update()
                if telemetry.is_paused:
                    continue
            except:
                telemetry = None
                continue

            # 1. 轉換為 BGR (解決 FFmpeg 3 vs 4 channels 錯誤)
            im_bgr = cv2.cvtColor(im_src, cv2.COLOR_BGRA2BGR)
            
            # 2. 轉換為俯視圖
            im_topdown = cv2.warpPerspective(im_bgr, HOMOGRAPHY, TOP_DOWN_SIZE) 

            # 3. 繪製標註
            # 畫出車輛邏輯中心 (綠色十字)
            tx, ty = int(TRUCK_CENTRE[0]), int(TRUCK_CENTRE[1])
            cv2.drawMarker(im_topdown, (tx, ty), (0, 255, 0), cv2.MARKER_CROSS, 40, 3)

            # 繪製所有路徑點 (藍色圓點)
            for point in centreline_image:
                px, py = int(point[0]), int(point[1])
                cv2.circle(im_topdown, (px, py), 3, (255, 0, 0), -1)  # 藍色實心圓

            # 控制邏輯

            # 計算轉向指令並發送
            steering, look_ahead_point = calc_input.CalcInput.pure_pursuit_control_car(
                telemetry, centreline, 10
            )
            send_input(telemetry, steering, 0)
            
            # 在畫面上即時印出轉向值
            cv2.putText(im_topdown, f"Steer: {steering:.4f}", (50, 100), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
            
            # 標記目標點（要轉向前往的方向）
            if look_ahead_point is not None:
                target_x, target_y = look_ahead_point
                # 從後軸坐標轉換到車輛中心坐標
                wheel_pos_z = telemetry.truck_wheel_position_z
                rear_axle_displacement = wheel_pos_z[2]
                center_target_x = target_x
                center_target_y = target_y - rear_axle_displacement  # 減去偏移，因為waypoints被加了偏移
                
                # 從車輛坐標轉換到圖像坐標（逆轉infer_polyline的轉換）
                # infer_polyline做了: centreline = np.multiply(centreline, (-0.25, -0.25)) 然後 np.subtract(centreline, TRUCK_CENTRE)
                # 所以逆轉換是: 先乘以(-4, -4)，然後加上TRUCK_CENTRE
                img_target_x = int(center_target_x * (-4) + TRUCK_CENTRE[0])
                img_target_y = int(center_target_y * (-4) + TRUCK_CENTRE[1])
                
                # 確保坐標在圖像範圍內
                if 0 <= img_target_x < TOP_DOWN_SIZE[0] and 0 <= img_target_y < TOP_DOWN_SIZE[1]:
                    cv2.drawMarker(im_topdown, (img_target_x, img_target_y), (0, 0, 255), cv2.MARKER_STAR, 30, 3)
                    cv2.putText(im_topdown, "Target", (img_target_x + 20, img_target_y), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
   

            # 4. 寫入影片檔案
            video_out.write(im_topdown)
            
            # 顯示視窗以便監控
            # cv2.imshow("Autopilot Debug", cv2.resize(im_topdown, (600, 600)))

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
                
    video_out.release()
    cv2.destroyAllWindows()
    print("Exiting...")

if __name__ == "__main__":
    main()