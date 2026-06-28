import cv2
import numpy as np

# This list will store our 4 points
points = []

def click_event(event, x, y, flags, params):
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([x, y])
        # Draw a small circle where you clicked
        cv2.circle(img, (x, y), 5, (0, 0, 255), -1)
        cv2.imshow("Calibration - Click 4 Corners", img)
        
        if len(points) == 4:
            print("\nCopy and paste this into your 'pts_src' variable:")
            print(f"pts_src = np.array({points}, dtype='float32')")
            print("\nPress any key to close.")

# Load a single frame from your camera
cap = cv2.VideoCapture(1)
ret, img = cap.read()
cap.release()

if not ret:
    print("Error: Could not access camera.")
    exit()

cv2.imshow("Calibration - Click 4 Corners", img)
print("Click the 4 corners of the belt in this order:")
print("1. Top-Left  2. Top-Right  3. Bottom-Right  4. Bottom-Left")

cv2.setMouseCallback("Calibration - Click 4 Corners", click_event)

cv2.waitKey(0)
cv2.destroyAllWindows()