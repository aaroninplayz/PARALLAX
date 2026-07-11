"""
PARALLAX — PyTorch Autoencoder Anomaly Detection
=====================================================
Uses a true Convolutional Neural Network (Deep Learning) natively utilizing GPU acceleration.

New Features:
- Massive Duration Recording: Saves frames at targeted intervals to prevent RAM explosions.
- Press 'SPACE' to force-stop acquiring and immediately start training the AI.
"""

import argparse
import cv2
import numpy as np
import time
import torch
import torch.nn as nn
import torch.optim as optim
import random
import os
from model import ConvAutoencoder, DifferenceClassifier

# ── Hyperparameters ──
AI_INPUT_SIZE = 128
PATCH_SIZE = 32
EPOCHS_TARGET = 30           
BATCH_SIZE = 32              

# Visuals
WINDOW_MAIN = "PARALLAX - AI Inference"
COLOR_LEARNING = (100, 200, 255)
COLOR_GPU = (255, 100, 255)
COLOR_NORMAL = (0, 255, 100)
COLOR_ANOMALY = (0, 0, 255)
COLOR_WHITE = (255, 255, 255)
COLOR_CONTOUR = (0, 165, 255) # Orange
COLOR_PATCH_PASS = (255, 200, 0) # Cyan for patch ignored

class ParallaxAI:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[PARALLAX AI] Initializing Neural Network Engine on: {str(self.device).upper()}")
        
        self.model = ConvAutoencoder().to(self.device)
        self.classifier = DifferenceClassifier().to(self.device)
        
        # Load trained classifier weights if available
        classifier_weights_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "classifier_weights.pth")
        if os.path.isfile(classifier_weights_path):
            self.classifier.load_state_dict(torch.load(classifier_weights_path, map_location=self.device, weights_only=True))
            print(f"[PARALLAX AI] Loaded trained classifier weights from {classifier_weights_path}")
        else:
            print("[PARALLAX AI] WARNING: No trained classifier weights found. Second brain outputs will be random.")
        self.classifier.eval()
        
        self.criterion = nn.MSELoss(reduction='none') 
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.002)
        
        self.state = "ACQUIRE" 
        self.dataset = []
        self.train_tensor = None
        
        self.epoch_count = 0
        self.smooth_score = 0.0

    def preprocess_for_ai(self, frame_bgr):
        # Convert BGR -> RGB and resize to AI input dimensions
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (AI_INPUT_SIZE, AI_INPUT_SIZE))
        normalized = resized.astype(np.float32) / 255.0
        # HWC -> CHW format for PyTorch: [3, H, W]
        tensor = torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0) 
        return tensor

    def preprocess_for_classifier(self, crop_bgr):
        if crop_bgr.size == 0:
            return torch.zeros(1, 3, PATCH_SIZE, PATCH_SIZE)
        # Convert BGR -> RGB and resize for the classifier
        rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (PATCH_SIZE, PATCH_SIZE))
        normalized = resized.astype(np.float32) / 255.0
        # HWC -> CHW format for PyTorch: [3, H, W]
        tensor = torch.from_numpy(normalized).permute(2, 0, 1).unsqueeze(0)
        return tensor

def main():
    parser = argparse.ArgumentParser(description="PARALLAX Deep AI")
    parser.add_argument("--source", default="0")
    parser.add_argument("--acquire_mins", type=float, default=1.0, help="Target recording duration in minutes (e.g. 120.0 for 2 hours)")
    parser.add_argument("--sample_fps", type=float, default=2.0, help="Frames to memorize per second. Prevents RAM explosion over long durations.")
    args = parser.parse_args()

    # Time parameters
    target_duration_sec = args.acquire_mins * 60.0
    capture_interval = 1.0 / args.sample_fps

    os.makedirs("training_data_collection", exist_ok=True)

    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    cv2.namedWindow(WINDOW_MAIN, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow(WINDOW_MAIN, 1280, 800)
    
    ai = ParallaxAI()
    _ = ai.model(torch.zeros(1, 3, AI_INPUT_SIZE, AI_INPUT_SIZE).to(ai.device))
    
    prev_time = time.time()
    last_capture_time = 0
    acquisition_start = time.time()
    
    print("[PARALLAX AI] System booted.")
    print(f"[PARALLAX] Will acquire data for {args.acquire_mins} minutes at {args.sample_fps} frames-per-second.")
    print(f"[PARALLAX] Hint: Press 'SPACEBAR' at any time to skip acquiring and force training immediately!")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        now = time.time()
        fps = 1.0 / max(now - prev_time, 1e-6)
        prev_time = now

        display = frame.copy()
        h, w = frame.shape[:2]

        status_text = ""
        status_color = COLOR_WHITE
        score_text = "Score: --"
        
        # ── Phase 1: ACQUIRE DATASET ──
        if ai.state == "ACQUIRE":
            elapsed = time.time() - acquisition_start
            remaining = max(0, target_duration_sec - elapsed)
            
            # Sub-sample the video feed so we don't destroy RAM over 2 hours
            if (time.time() - last_capture_time) > capture_interval:
                tensor_frame = ai.preprocess_for_ai(frame)
                ai.dataset.append(tensor_frame)
                
                last_capture_time = time.time()
            
            progress = min(1.0, elapsed / target_duration_sec)
            status_text = f"ACQUIRING NEURAL DATA ({int(progress*100)}%) - {int(remaining/60)}m {int(remaining%60)}s left"
            status_color = COLOR_LEARNING

            # Press SPACE check happens down in the keybind area
            if elapsed >= target_duration_sec:
                print(f"\n[PARALLAX AI] Dataset Constructed ({len(ai.dataset)} frames). Porting to VRAM...")
                ai.train_tensor = torch.cat(ai.dataset, dim=0).to(ai.device)
                ai.state = "TRAIN"

        # ── Phase 2: LIVE GPU TRAINING ──
        elif ai.state == "TRAIN":
            ai.model.train()
            indices = torch.randperm(ai.train_tensor.size(0))
            epoch_loss = 0.0
            
            for i in range(0, ai.train_tensor.size(0), BATCH_SIZE):
                batch_idx = indices[i:i+BATCH_SIZE]
                batch_data = ai.train_tensor[batch_idx]
                
                ai.optimizer.zero_grad()
                reconstructed = ai.model(batch_data)
                loss = torch.nn.functional.mse_loss(reconstructed, batch_data)
                loss.backward()
                ai.optimizer.step()
                
                epoch_loss += loss.item()
                
            ai.epoch_count += 1
            status_text = f"GPU TRAINING: EPOCH {ai.epoch_count}/{EPOCHS_TARGET} | LOSS: {epoch_loss:.5f}"
            status_color = COLOR_GPU
            
            if ai.epoch_count >= EPOCHS_TARGET:
                print("[PARALLAX AI] Neural Constraints Met. Baseline Overfitted.")
                ai.model.eval()
                ai.state = "INFER"
                del ai.train_tensor
                ai.dataset.clear()
                torch.cuda.empty_cache()

        # ── Phase 3: LIVE A.I. INFERENCE ──
        elif ai.state == "INFER":
            tensor_frame = ai.preprocess_for_ai(frame).to(ai.device)
            
            with torch.no_grad():
                reconstructed = ai.model(tensor_frame)
                loss_map_tensor = ai.criterion(reconstructed, tensor_frame)
                # Average across 3 color channels to get a single-channel anomaly heatmap
                # Shape: [1, 3, H, W] -> mean over channel dim -> [H, W]
                loss_map_raw = loss_map_tensor.squeeze().mean(dim=0).cpu().numpy()
                
            loss_map_visual = (loss_map_raw * 255.0 * 5.0) 
            loss_map_visual = np.clip(loss_map_visual, 0, 255).astype(np.uint8)
            loss_map_visual = cv2.GaussianBlur(loss_map_visual, (5, 5), 0)
            
            _, binary_anomaly = cv2.threshold(loss_map_visual, 50, 255, cv2.THRESH_BINARY)
            binary_anomaly_large = cv2.resize(binary_anomaly, (w, h), interpolation=cv2.INTER_NEAREST)
            
            contours, _ = cv2.findContours(binary_anomaly_large, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            is_anomalous = False
            for cnt in contours:
                if cv2.contourArea(cnt) > 2000: 
                    # Extract bounding box with padding
                    x, y, bw, bh = cv2.boundingRect(cnt)
                    pad = 20
                    x1 = max(0, x - pad)
                    y1 = max(0, y - pad)
                    x2 = min(w, x + bw + pad)
                    y2 = min(h, y + bh + pad)
                    
                    crop = frame[y1:y2, x1:x2]
                    crop_tensor = ai.preprocess_for_classifier(crop).to(ai.device)
                    
                    # Ask secondary Large Model (Untrained for now)
                    # It returns a logit, we apply sigmoid in the model so we get a probability [0.0, 1.0]
                    with torch.no_grad():
                        prob_anomaly = ai.classifier(crop_tensor).item()
                    
                    # Save the crop for future training data
                    timestamp = int(time.time() * 1000)
                    cv2.imwrite(f"training_data_collection/crop_{timestamp}.jpg", crop)
                    
                    # Threshold for probability (e.g. > 0.5 means true anomaly)
                    # Since it's untrained, the result is somewhat random right now, but architecture is ready!
                    if prob_anomaly > 0.5:
                        is_anomalous = True
                        cv2.rectangle(display, (x1, y1), (x2, y2), COLOR_CONTOUR, 3)
                        cv2.putText(display, f"True Anomaly ({prob_anomaly:.3f})", (x1, max(20, y1-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_CONTOUR, 2)
                    else:
                        cv2.rectangle(display, (x1, y1), (x2, y2), COLOR_PATCH_PASS, 2)
                        cv2.putText(display, f"Filtered ({prob_anomaly:.3f})", (x1, max(20, y1-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_PATCH_PASS, 2)
                    
            max_frame_error = loss_map_raw.max()
            ai.smooth_score = (ai.smooth_score * 0.9) + (max_frame_error * 0.1)
            
            score_text = f"Neural Loss: {ai.smooth_score:.4f}"
            
            if is_anomalous:
                status_text = "ANOMALY DETECTED"
                status_color = COLOR_ANOMALY
            else:
                status_text = "NORMAL ENVIRONMENT"
                status_color = COLOR_NORMAL
                
            
        # ── BUILD UI DASHBOARD ──
        dashboard_height = 80
        dashboard = np.zeros((dashboard_height, w, 3), dtype=np.uint8)
        
        cv2.putText(dashboard, status_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, status_color, 3, cv2.LINE_AA)
        cv2.putText(dashboard, score_text, (w // 2 - 100, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, COLOR_WHITE, 2, cv2.LINE_AA)
        cv2.putText(dashboard, f"FPS: {int(fps)}", (w - 150, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (150, 150, 150), 2, cv2.LINE_AA)

        final_layout = np.vstack([display, dashboard])
        cv2.imshow(WINDOW_MAIN, final_layout)
        
        # ── Keyboard Controls ──
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            print("[PARALLAX AI] Engine Reset. Erasing Neural Baseline...")
            ai.state = "ACQUIRE"
            ai.dataset.clear()
            acquisition_start = time.time()
            ai.epoch_count = 0
            ai.smooth_score = 0.0
            ai.model = ConvAutoencoder().to(ai.device)
            ai.optimizer = optim.Adam(ai.model.parameters(), lr=0.002)
        elif key == ord(' '): 
            # Spacebar to Force Stop Acquisition
            if ai.state == "ACQUIRE" and len(ai.dataset) > 10:
                print(f"[PARALLAX AI] Force-stopped acquisition. Compiling {len(ai.dataset)} frames...")
                ai.train_tensor = torch.cat(ai.dataset, dim=0).to(ai.device)
                ai.state = "TRAIN"

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
