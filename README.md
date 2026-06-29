# **GUAVA PASTE CLASSIFICATION SYSTEM**

Automated industrial inspection system for guava paste quality control using computer vision and PLC integration.

---

## **PROJECT OVERVIEW**

This system utilizes a USB webcam to detect, measure, and classify guava paste pieces on a conveyor belt. It integrates with a Delta AS200 PLC via the Modbus TCP protocol to trigger automated sorting based on dimensional analysis.

---

## **SYSTEM ARCHITECTURE**

* **Hardware:** USB Webcam, Delta AS200 PLC, Industrial Conveyor.
* **Communication:** Modbus TCP protocol for real-time PLC interaction.
* **Processing:** Python, OpenCV (HSV masking, contour analysis).

---

## **CALIBRATION & SETUP GUIDE**

### **LENS CALIBRATION (FISH-EYE REMOVAL)**
To ensure accurate measurements, the lens distortion must be removed using the chessboard technique.
* Run the calibration script using a 9x6 chessboard pattern.
* Capture at least 15 frames at various angles by pressing 's'.
* The script generates `calib_data.npz`, which the main system uses to undistort the input feed.

### **PERSPECTIVE SETUP (BIRD'S EYE VIEW)**
To measure dimensions correctly, the camera view must be flattened.
* Use the coordinate picker script to identify the 4 corners of the conveyor belt.
* Update the `pts_src` array in the main script with these coordinates to enable the perspective warp transformation.

### **SCALE CALIBRATION**
* Place a ruler on the belt.
* In the warped window, identify the number of pixels corresponding to a known distance (e.g., 8cm).
* Update the `pixeles_por_cm` variable in the script to calibrate measurements.

---

## **OPERATION & LOGGING**

* **Detection:** The system applies an HSV mask (`lower_bocadillo` to `upper_bocadillo`) to identify pieces.
* **Classification:** Pieces are measured in real-time; those within the defined `ancho_min/max` and `alto_min/max` tolerances are marked as "PASS," others as "REJECT".
* **Data Logging:** Results are recorded in the `registro_produccion_bocadillos.csv` file, providing a detailed history of production performance.
* **PLC Integration:** The system uses `PLCCommunicator` to send classification results to D498 and trigger the M1412 bit for the PLC's FIFO queue.
