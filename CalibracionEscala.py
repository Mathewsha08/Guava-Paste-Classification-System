import cv2
import numpy as np

# --- 1. PERSPECTIVE CONFIGURATION ---
# Use the 4 points you found with ROI_Clicker.py
# Order: [Top-Left, Top-Right, Bottom-Right, Bottom-Left]
#pts_src = np.array([[11, 15], [625, 16], [624, 462], [12, 462]], dtype='float32')
pts_src = np.array([[1, 70], [638, 54], [638, 419], [1, 442]], dtype='float32')

# --- LOAD LENS CALIBRATION DATA ---
try:
    with np.load('calib_data.npz') as data:
        mtx = data['mtx']
        dist = data['dist']
    print("Lens calibration data loaded successfully.")
except FileNotFoundError:
    print("ERROR: Run ScriptDeCalibracion.py first to generate calib_data.npz")
    exit()

# Desired size of the flattened "Bird-Eye" window
width_dst, height_dst = 600, 400 
pts_dst = np.array([
    [0, 0], 
    [width_dst, 0], 
    [width_dst, height_dst], 
    [0, height_dst]
], dtype="float32")


# State variables for clicking
points = []
img_warped = None

def click_event(event, x, y, flags, param):
    global points, img_warped
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        cv2.circle(img_warped, (x, y), 5, (0, 0, 255), -1)
        
        if len(points) == 2:
            # Calculate Euclidean distance in pixels
            dist_px = np.sqrt((points[1][0] - points[0][0])**2 + (points[1][1] - points[0][1])**2)
            cv2.line(img_warped, points[0], points[1], (0, 255, 0), 2)
            
            print(f"\n" + "="*40)
            print(f"PIXEL DISTANCE (BIRD-EYE): {dist_px:.2f} px")
            print(f"For a 8cm ruler: Pixels/CM = {round(dist_px / 8, 2)}")
            print("="*40)
            points = [] # Reset
        
        cv2.imshow("Scale Calibration (Bird-Eye)", img_warped)

# Initialize Camera
cap = cv2.VideoCapture(1) 

print("INSTRUCTIONS:")
print("1. Place a ruler on the conveyor belt.")
print("2. In the 'Bird-Eye' window, click the 0cm mark and the 8cm mark.")
print("3. Use the Pixels/CM result in your main production script.")
print("4. Press 'q' to exit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # STEP A: Remove Lens Distortion FIRST
    frame_undistorted = cv2.undistort(frame, mtx, dist, None, mtx)

    # Apply Perspective Transformation
    matrix = cv2.getPerspectiveTransform(pts_src, pts_dst)
    img_warped = cv2.warpPerspective(frame_undistorted, matrix, (width_dst, height_dst))
    
    cv2.imshow("Scale Calibration (Bird-Eye)", img_warped)
    cv2.setMouseCallback("Scale Calibration (Bird-Eye)", click_event)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()