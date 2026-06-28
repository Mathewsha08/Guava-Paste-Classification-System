Guava Paste Classification System
Automated industrial inspection system for guava paste quality control using computer vision and PLC integration.

Project Overview
This system utilizes a USB webcam to detect, measure, and classify guava paste pieces on a conveyor belt. It integrates with a Delta AS200 PLC via the Modbus TCP protocol to trigger automated sorting based on dimensional analysis.  
TXT
+ 1

System Architecture
Hardware: USB Webcam, Delta AS200 PLC, Industrial Conveyor.  
TXT

Communication: Modbus TCP protocol for real-time PLC interaction.  
TXT
+ 1

Processing: Python, OpenCV (HSV masking, contour analysis).  
TXT

Calibration & Setup Guide
1. Lens Calibration (Fish-eye Removal)
To ensure accurate measurements, the lens distortion must be removed using the chessboard technique.  
PY

Run the calibration script using a 9x6 chessboard pattern.  
PY

Capture at least 15 frames at various angles by pressing 's'.  
PY

The script generates calib_data.npz, which the main system uses to undistort the input feed.  
PY
+ 1

2. Perspective Setup (Bird's Eye View)
To measure dimensions correctly, the camera view must be flattened.  
PY

Use the coordinate picker script to identify the 4 corners of the conveyor belt.  
PY
+ 1

Update the pts_src array in the main script with these coordinates to enable the perspective warp transformation.  
TXT
+ 2

3. Scale Calibration
Place a ruler on the belt.  
PY
+ 1

In the warped window, identify the number of pixels corresponding to a known distance (e.g., 8cm).  
PY

Update the pixeles_por_cm variable in the script to calibrate measurements.  
TXT
+ 1

Operation & Logging
Detection: The system applies an HSV mask (lower_bocadillo to upper_bocadillo) to identify pieces.  
TXT
+ 1

Classification: Pieces are measured in real-time; those within the defined ancho_min/max and alto_min/max tolerances are marked as "PASS," others as "REJECT".  
TXT

Data Logging: Results are recorded in the registro_produccion_bocadillos.csv file, providing a detailed history of production performance.  
PY
+ 1

PLC Integration: The system uses PLCCommunicator to send classification results to D498 and trigger the M1412 bit for the PLC's FIFO queue.  
PY

Tips for your next GitHub update:
Folder Structure: Ensure your repository includes a requirements.txt file listing dependencies like opencv-python, pandas, and pymodbus so others can easily set up the environment.

Images: Since you are saving images to capturas_produccion, consider adding a small section in your README showing a "Before vs. After" image of the warped and undistorted processing pipeline.

Would you like help generating a requirements.txt file for this project, or are you ready to push these changes to GitHub?Guava Paste Classification System
Automated industrial inspection system for guava paste quality control using computer vision and PLC integration.

Project Overview
This system utilizes a USB webcam to detect, measure, and classify guava paste pieces on a conveyor belt. It integrates with a Delta AS200 PLC via the Modbus TCP protocol to trigger automated sorting based on dimensional analysis.  
TXT
+ 1

System Architecture
Hardware: USB Webcam, Delta AS200 PLC, Industrial Conveyor.  
TXT

Communication: Modbus TCP protocol for real-time PLC interaction.  
TXT
+ 1

Processing: Python, OpenCV (HSV masking, contour analysis).  
TXT

Calibration & Setup Guide
1. Lens Calibration (Fish-eye Removal)
To ensure accurate measurements, the lens distortion must be removed using the chessboard technique.  
PY

Run the calibration script using a 9x6 chessboard pattern.  
PY

Capture at least 15 frames at various angles by pressing 's'.  
PY

The script generates calib_data.npz, which the main system uses to undistort the input feed.  
PY
+ 1

2. Perspective Setup (Bird's Eye View)
To measure dimensions correctly, the camera view must be flattened.  
PY

Use the coordinate picker script to identify the 4 corners of the conveyor belt.  
PY
+ 1

Update the pts_src array in the main script with these coordinates to enable the perspective warp transformation.  
TXT
+ 2

3. Scale Calibration
Place a ruler on the belt.  
PY
+ 1

In the warped window, identify the number of pixels corresponding to a known distance (e.g., 8cm).  
PY

Update the pixeles_por_cm variable in the script to calibrate measurements.  
TXT
+ 1

Operation & Logging
Detection: The system applies an HSV mask (lower_bocadillo to upper_bocadillo) to identify pieces.  
TXT
+ 1

Classification: Pieces are measured in real-time; those within the defined ancho_min/max and alto_min/max tolerances are marked as "PASS," others as "REJECT".  
TXT

Data Logging: Results are recorded in the registro_produccion_bocadillos.csv file, providing a detailed history of production performance.  
PY
+ 1

PLC Integration: The system uses PLCCommunicator to send classification results to D498 and trigger the M1412 bit for the PLC's FIFO queue.  
PY

Tips for your next GitHub update:
Folder Structure: Ensure your repository includes a requirements.txt file listing dependencies like opencv-python, pandas, and pymodbus so others can easily set up the environment.

Images: Since you are saving images to capturas_produccion, consider adding a small section in your README showing a "Before vs. After" image of the warped and undistorted processing pipeline.

Would you like help generating a requirements.txt file for this project, or are you ready to push these changes to GitHub?
