import cv2
import numpy as np
import os

print("Testing avc1 codec...")
fourcc = cv2.VideoWriter_fourcc(*'avc1')
out = cv2.VideoWriter('test_avc1.mp4', fourcc, 20.0, (640, 480))
if not out.isOpened():
    print("FAILED to open avc1 writer!")
else:
    for i in range(20):
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        out.write(frame)
    out.release()
    print("SUCCESS avc1 file created. Size:", os.path.getsize('test_avc1.mp4'))

print("Testing vp80 codec...")
fourcc = cv2.VideoWriter_fourcc(*'vp80')
out = cv2.VideoWriter('test_vp80.webm', fourcc, 20.0, (640, 480))
if not out.isOpened():
    print("FAILED to open vp80 writer!")
else:
    for i in range(20):
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        out.write(frame)
    out.release()
    print("SUCCESS vp80 file created. Size:", os.path.getsize('test_vp80.webm'))
