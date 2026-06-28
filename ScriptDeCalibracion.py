import cv2
import numpy as np
import glob

# Termination criteria for sub-pixel corner detection
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# Prepare object points (0,0,0), (1,0,0) ... based on your chessboard size
rows, cols = 5,8 
objp = np.zeros((rows * cols, 3), np.float32)
objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)

objpoints = [] # 3d point in real world space
imgpoints = [] # 2d points in image plane

cap = cv2.VideoCapture(1)
print("Press 's' to save a calibration frame, 'q' to finish and calculate.")

while True:
    ret, frame = cap.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    ret_corners, corners = cv2.findChessboardCorners(gray, (cols, rows), None)

    # Line to look for corners and give feedback in the terminal:
    if not ret_corners:
        print("Searching for corners...", end="\r") 

    if ret_corners:
        print("CORNERS FOUND! Press 's' now.") # This will tell you it's working
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        cv2.drawChessboardCorners(frame, (cols, rows), corners2, ret_corners)

    if ret_corners:
        # Refine corners for better accuracy
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        cv2.drawChessboardCorners(frame, (cols, rows), corners2, ret_corners)

    cv2.imshow('Calibration', frame)
    key = cv2.waitKey(1)
    if key == ord('s') and ret_corners:
        objpoints.append(objp)
        imgpoints.append(corners2)
        print(f"Captured frame {len(objpoints)}")
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# Calculate calibration parameters
ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)

# Save the results
np.savez('calib_data.npz', mtx=mtx, dist=dist)
print("Calibration saved to calib_data.npz")