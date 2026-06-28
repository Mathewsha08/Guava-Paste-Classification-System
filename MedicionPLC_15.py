import cv2
import numpy as np
import os
import pandas as pd 
from datetime import datetime
from plc_communicator import PLCCommunicator, CommunicationProtocol
import time

# --- LOAD LENS CALIBRATION DATA ---
try:
    with np.load('calib_data.npz') as data:
        mtx = data['mtx']
        dist = data['dist']
    print("Lens calibration data loaded successfully.")
except FileNotFoundError:
    print("WARNING: calib_data.npz not found. Measurements may be inaccurate due to lens distortion.")
    mtx, dist = None, None

# --- CONFIGURATION ---
pts_src = np.array([[1, 70], [638, 54], [638, 419], [1, 442]], dtype='float32')
width_dst, height_dst = 600, 400 
pts_dst = np.array([[0, 0], [width_dst, 0], [width_dst, height_dst], [0, height_dst]], dtype="float32")
M_perspective = cv2.getPerspectiveTransform(pts_src, pts_dst)

#pixeles_por_cm = 62.45
pixeles_por_cm = 68.0 
length_offset = -0.5 
width_offset = -0.66

ancho_min, ancho_max = 2.74, 3.06
alto_min, alto_max = 4.34, 4.66
# Classification & CSV Settings
#ancho_min, ancho_max = 2.70, 3.10
#alto_min, alto_max = 4.30, 4.70
# Increase area_minima if 1400 is still catching crumbs
area_minima = 1800
log_file = "registro_produccion_bocadillos.csv"

# --- NEW: OUTPUT FOLDER SETUP ---
output_folder = "capturas_produccion"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Right-to-Left Tracking & Sticky Memory
trigger_line_x = 240
trigger_width = 60 # Narrowed to number of pixels for more precise triggering
forget_timeout = 0.3  # Piece must be 'gone' for 0.4 seconds before resetting lane
plc_burst_delay = 0.15   # 150ms delay to prevent overwhelming the PLC
tracked_objects = {}  # {obj_id: last_seen_timestamp}

# Counters for monitoring
total_detected = 0


# --- Tracking clumbs---
last_action_time = time.time()

# --- INITIALIZATION ---
plc = PLCCommunicator(protocol=CommunicationProtocol.MODBUS_TCP) 
plc_connected = False
try:
    plc_connected = plc.connect_tcp(host="192.168.2.142", port=502)
    if plc_connected:
        print("PLC Communication Verified on M1400-M1403")
except Exception as e:
    print(f"PLC Connection Failed: {e}")

cap = cv2.VideoCapture(1)
lower_bocadillo = np.array([0, 50, 50])
upper_bocadillo = np.array([20, 255, 255])
last_heartbeat_time = time.time()
heartbeat_state = False
last_conveyor_check = 0
conveyor_running = True # Default to True so it tries to start with the conveyor running


# --- NEW CONFIGURATION VARIABLES FOR CLEAN DETECTION ---
# Ignore anything smaller than this to avoid FIFO desync
hard_min_width = 1.8  
hard_min_length = 3.0 
# Minimum time (seconds) between two real bocadillos (adjust based on conveyor speed)
min_inter_object_delay = 0.10 
last_trigger_time = 0

# --- COUNTERS ---
total_count = 0
passed_count = 0
rejected_count = 0

print("System Running... Press 'q' to quit.")



while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break


    # Step A: Remove Lens Distortion
    if mtx is not None:
        frame = cv2.undistort(frame, mtx, dist, None, mtx)

    # --- 1. ALWAYS CREATE THE IMAGE FIRST ---
    # Step B: Apply Perspective Warp
    warped = cv2.warpPerspective(frame, M_perspective, (width_dst, height_dst))

    
    # --- STEP 2: GLOBAL HEARTBEAT (Always Runs) ---
        # --- HEARTBEAT (M1406) ---
    if time.time() - last_heartbeat_time > 1.5:
        heartbeat_state = not heartbeat_state
        if plc_connected:
            try: plc.write_output('heartbeat', heartbeat_state)
            except: pass
        last_heartbeat_time = time.time()

    # 3. THROTTLED CONVEYOR CHECK (Every 300ms)
        # Checking Modbus too fast can freeze the UI thread
        if plc_connected and (time.time() - last_conveyor_check > 0.15):
            status = plc.read_bit('conveyor_running')
            if status is not None:
                conveyor_running = status
            last_conveyor_check = time.time()
    

    # 4. CONDITIONAL DETECTION LOGIC
    if conveyor_running:
    #if True: # For testing, run detection even if conveyor is stopped. Change back to conveyor_running in production.:
        # Run your HSV, Mask, Contours, and FIFO Logic here


    
        # --- 4. DETECTION LOGIC ---
        # This part ONLY runs if conveyor_running is True
        hsv = cv2.cvtColor(warped, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_bocadillo, upper_bocadillo)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)


        current_frame_ids = []

        for c in contours:
            area = cv2.contourArea(c)
            if area >= area_minima:
                M = cv2.moments(c)
                if M["m00"] == 0: continue
                cX, cY = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
                
                # --- FIX: HIGH RESOLUTION LANES ---
                # // 10 creates very narrow lanes so pieces don't block each other
                obj_id = f"Lane_Y_{cY // 10}" 
                current_frame_ids.append(obj_id)

                # Measurements
                rect = cv2.minAreaRect(c)
                w, h = sorted(rect[1])
                ancho_cm = (w / pixeles_por_cm) + width_offset
                alto_cm = (h / pixeles_por_cm) + length_offset
                
                # size Sanity Check - Ignore anything that isn't roughly rectangular/bocadillo-shaped
                # Even if it's "bad," a fragment of 0.5cm is NOT a bocadillo and shouldn't enter the FIFO
                if ancho_cm < 1.5 or alto_cm < 2.5:
                    #print(f"Ignored small detection at ({cX}, {cY}) with size {ancho_cm:.2f}x{alto_cm:.2f}cm")
                    continue # Skip this detection entirely; don't log, don't tell the PLC


                # VISUALS
                box = np.intp(cv2.boxPoints(rect))
                cv2.drawContours(warped, [box], 0, (0, 255, 0), 2)
                cv2.putText(warped, f"{ancho_cm:.2f}x{alto_cm:.2f}cm", (cX - 40, cY - 20), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
                

                # --- HIGH-SPEED TRIGGER ZONE ---
                # --- ROBUST TRIGGER LOGIC ---
                # 1. TIME & ID FILTER: Only trigger if it's a new piece and not a double-flicker
                if (trigger_line_x - trigger_width) < cX < trigger_line_x:
                    current_time = time.time()
                    if obj_id not in tracked_objects and (current_time - last_trigger_time) > min_inter_object_delay:

                        is_good = (ancho_min <= ancho_cm <= ancho_max and alto_min <= alto_cm <= alto_max)
                        result_text = "PASS" if is_good else "REJECT"

                        # UPDATE COUNTERS
                        total_count += 1
                        if is_good:
                            passed_count += 1
                            result_text = "PASS"
                        else:
                            rejected_count += 1
                            result_text = "REJECT"
                        # 2. PLC COMMUNICATION
                        if plc_connected:
                            try:
                                # FIX: Return to the method that is actually defined in your communicator
                                # This automatically writes to D498 and pulses M1412
                                plc.send_to_fifo(is_good)
                                
                                # Update the last trigger time to prevent immediate double-triggers
                                last_trigger_time = current_time
                            except Exception as e:
                                print(f"PLC Communication Error: {e}")

                        print(f"ACTION #{total_count}: {result_text} | Total: {total_count} (P: {passed_count}, R: {rejected_count})")
                        # 3. COUNTERS AND TRACKING
                        total_detected += 1
                        tracked_objects[obj_id] = current_time
                        print(f"ACTION #{total_detected}: {result_text} ({ancho_cm:.2f}x{alto_cm:.2f})")
                        
                        current_action_time = time.time()
                        time_since_last = current_action_time - last_action_time

                        print(f"ACTION #{total_count}: {result_text} | Gap: {time_since_last:.2f}s")
                        last_action_time = current_action_time
                        # 2. LOGGING
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log_entry = pd.DataFrame([[timestamp, round(ancho_cm, 2), round(alto_cm, 2), result_text]], 
                                                columns=["Time", "Width", "Length", "Result"])
                        # --- IMPROVED LOGGING LOGIC ---
                        try:
                            log_entry.to_csv(log_file, mode='a', header=not os.path.exists(log_file), index=False)
                        except PermissionError:
                            print(f"CRITICAL WARNING: Could not save to {log_file}. Please close the file if it is open in Excel.")
                        except Exception as e:
                            print(f"Unexpected error saving log: {e}")

                            # --- NEW: SAVE IMAGE TO FOLDER ---
                        # Include the PASS/REJECT status and dimensions in the filename for easy review
                        ts_file = datetime.now().strftime("%H%M%S")
                        img_path = f"{output_folder}/{result_text}_{ts_file}_{ancho_cm:.2f}x{alto_cm:.2f}.jpg"
                        
                        # Save the current warped frame (which already contains the drawn boxes and text)
                        cv2.imwrite(img_path, warped)
                        # Optional: Print to console that the image was saved
                        print(f"Image saved: {img_path}")

                    else:
                        # Refresh the timer as long as the piece is in the zone
                        tracked_objects[obj_id] = time.time()

        # --- STICKY CLEANUP ---
        current_time = time.time()
        tracked_objects = {oid: ts for oid, ts in tracked_objects.items() 
                        if (current_time - ts) < forget_timeout}

        # Visual Feedback of the Zone
        cv2.line(warped, (trigger_line_x, 0), (trigger_line_x, height_dst), (0, 0, 255), 2)
        cv2.line(warped, (trigger_line_x - trigger_width, 0), (trigger_line_x - trigger_width, height_dst), (0, 255, 255), 1)



    # --- ONSCREEN DASHBOARD ---
    # Semi-transparent background for readability
    # 1. Background for stats
    cv2.rectangle(warped, (5, 5), (230, 115), (0, 0, 0), -1) 

    # 2. Status Color
    status_color = (0, 255, 0) if conveyor_running else (0, 0, 255)
    status_text = "RUNNING" if conveyor_running else "STOPPED"

    # 3. Text Overlay
    cv2.putText(warped, f"STATUS: {status_text}", (15, 25), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 2)
    cv2.putText(warped, f"TOTAL: {total_count}", (15, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(warped, f"PASS:  {passed_count}", (15, 75), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.putText(warped, f"REJ:   {rejected_count}", (15, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # 4. Big central message if stopped
    if not conveyor_running:
        cv2.putText(warped, "CONVEYOR STOPPED", (140, 220), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 4)
    # 5. DISPLAY
    # cv2.line(warped, (trigger_line_x, 0), (trigger_line_x, height_dst), (0, 0, 255), 2)
    cv2.imshow("Production Feed", warped)
    # Display total count on the feed
    cv2.putText(warped, f"Count: {total_detected}", (10, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # INCREASE waitKey to 30ms and check for the "X" button
    key = cv2.waitKey(30) & 0xFF
    
    # This allows closing with 'q' OR by clicking the red X on the window
    if key == ord('q') or cv2.getWindowProperty("Production Feed", cv2.WND_PROP_VISIBLE) < 1:
        print("Shutdown requested by user.")
        break



cap.release()
cv2.destroyAllWindows()
if plc_connected:
    plc.disconnect() # Ensure the Modbus socket is closed cleanly