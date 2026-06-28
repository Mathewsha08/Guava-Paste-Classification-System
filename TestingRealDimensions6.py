import cv2
import numpy as np
import os
import pandas as pd 
from datetime import datetime
import sys

# --- LOAD LENS CALIBRATION DATA ---
try:
    with np.load('calib_data.npz') as data:
        mtx = data['mtx']
        dist = data['dist']
    print("Lens calibration data loaded successfully.")
except FileNotFoundError:
    print("WARNING: calib_data.npz not found. Measurements may be inaccurate due to lens distortion.")
    mtx, dist = None, None

# --- 1. CONFIGURACIÓN DE VISIÓN ---
#pts_src = np.array([[11, 15], [625, 16], [624, 462], [12, 462]], dtype='float32')
pts_src = np.array([[1, 70], [638, 54], [638, 419], [1, 442]], dtype='float32')
width_dst, height_dst = 600, 400 
pts_dst = np.array([[0, 0], [width_dst, 0], [width_dst, height_dst], [0, height_dst]], dtype="float32")
M_perspective = cv2.getPerspectiveTransform(pts_src, pts_dst)

pixeles_por_cm = 68.0 # Adjust based on your actual belt width and chosen warped resolution
length_offset = -0.5
width_offset = -0.66
area_minima = 1800

lower_bocadillo = np.array([0, 50, 50])
upper_bocadillo = np.array([20, 255, 255])

validation_log = "validacion_medidas11_05_2026.csv"
output_folder = "capturas_validacion11_05_2026"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

trigger_line_x = 240
trigger_width = 80 # Widened to allow for peak measurement tracking

# State variables for Peak Detection
waiting_for_piece = False
peak_measurement = {"w": 0, "l": 0, "frame": None, "box": None, "contour": None, "cX": 0, "cY": 0}
piece_in_trigger = False

cap = cv2.VideoCapture(1) 

print("--- SISTEMA GUSTAR S.A.S: VALIDACIÓN DE MÁXIMOS ---")

try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

            # Step A: Remove Lens Distortion
        if mtx is not None:
            frame = cv2.undistort(frame, mtx, dist, None, mtx)

        warped = cv2.warpPerspective(frame, M_perspective, (width_dst, height_dst))
        hsv = cv2.cvtColor(warped, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_bocadillo, upper_bocadillo)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Draw Trigger Area
        cv2.line(warped, (trigger_line_x, 0), (trigger_line_x, 400), (0, 0, 255), 2)
        cv2.line(warped, (trigger_line_x - trigger_width, 0), (trigger_line_x - trigger_width, 400), (0, 255, 255), 1)

        if not waiting_for_piece:
            cv2.putText(warped, "INGRESE DATOS EN CONSOLA", (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.imshow("Production Feed", warped)
            cv2.waitKey(1)
            
            print("\n" + "="*50)
            entry_w = input("Ancho Real (mm) [o 'exit']: ")
            if entry_w.lower() == 'exit': break
            try:
                last_real_w = float(entry_w) / 10.0
                last_real_l = float(input("Largo Real (mm): ")) / 10.0
                waiting_for_piece = True
                # Reset peak tracking for new piece
                peak_measurement = {"w": 0, "l": 0, "frame": None, "box": None, "contour": None}
                print(f"-> Esperando pieza de {entry_w}x{last_real_l*10}mm...")
            except ValueError: continue

        piece_found_this_frame = False
        for c in contours:
            area = cv2.contourArea(c)
            if area >= area_minima:
                piece_found_this_frame = True
                rect = cv2.minAreaRect(c)
                box = np.intp(cv2.boxPoints(rect))
                
                # Live drawing for feedback
                cv2.drawContours(warped, [c], -1, (255, 0, 0), 1) # Thin Blue
                cv2.drawContours(warped, [box], 0, (0, 255, 0), 2) # Thick Green
                
                w_raw, l_raw = sorted(rect[1])
                curr_w = round((w_raw / pixeles_por_cm) + width_offset, 2)
                curr_l = round((l_raw / pixeles_por_cm) + length_offset, 2)
                
                M = cv2.moments(c)
                cX = int(M["m10"] / M["m00"]) if M["m00"] != 0 else 0
                cY = int(M["m01"] / M["m00"]) if M["m00"] != 0 else 0

                # --- PEAK DETECTION LOGIC ---
                if (trigger_line_x - trigger_width) < cX < trigger_line_x and waiting_for_piece:
                    piece_in_trigger = True
                    # If this frame has a larger area (better view), save it as the peak
                    if area > peak_measurement.get("area", 0):
                        peak_measurement = {
                            "w": curr_w, "l": curr_l, "area": area,
                            "frame": warped.copy(), "box": box, "contour": c,
                            "cX": cX, "cY": cY
                        }
                
                # Piece has exited trigger zone -> Finalize Capture
                elif piece_in_trigger and cX < (trigger_line_x - trigger_width):
                    piece_in_trigger = False
                    
                    print(f"CAPTURA DE MÁXIMO: {peak_measurement['w']}x{peak_measurement['l']} cm")

                    # FASE 4: ENTRADA POSICIÓN
                    try:
                        pos_mm = float(input("Posición en banda (mm): "))
                        pos_cm = round(pos_mm / 10.0, 2)
                    except ValueError: pos_cm = 0.0

                    # SAVE IMAGE WITH BOTH CONTOURS
                    final_img = peak_measurement["frame"]
                    cv2.drawContours(final_img, [peak_measurement["contour"]], -1, (255, 0, 0), 1) # Blue
                    cv2.drawContours(final_img, [peak_measurement["box"]], 0, (0, 255, 0), 2) # Green
                    
                    meas_text = f"{peak_measurement['w']}x{peak_measurement['l']}cm"
                    cv2.putText(final_img, meas_text, (peak_measurement['cX'] - 80, peak_measurement['cY']), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                    ts = datetime.now().strftime("%H%M%S")
                    img_path = f"{output_folder}/Max_{ts}_{peak_measurement['w']}x{peak_measurement['l']}.jpg"
                    cv2.imwrite(img_path, final_img)

                    # SAVE TO CSV
                    diff_w = round(last_real_w - peak_measurement['w'], 3)
                    diff_l = round(last_real_l - peak_measurement['l'], 3)
                    
                    data = [[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), last_real_w, peak_measurement['w'], 
                             diff_w, last_real_l, peak_measurement['l'], diff_l, pos_cm, img_path]]
                    pd.DataFrame(data).to_csv(validation_log, mode='a', header=not os.path.exists(validation_log), 
                                              index=False, sep=';', decimal=',')
                    
                    print(f"Registro completo guardado en: {img_path}")
                    waiting_for_piece = False

        cv2.imshow("Production Feed", warped)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

except Exception as e: print(f"Error: {e}")
finally:
    cap.release()
    cv2.destroyAllWindows()