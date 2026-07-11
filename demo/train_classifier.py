"""
PARALLAX — Interactive DifferenceClassifier Training
=====================================================
Captures NORMAL scene patches from webcam (one-class approach).
Synthesizes anomaly patches automatically. Trains ResNet-18 binary classifier.
Pauses every N epochs to show accuracy and let user decide to stop or continue.

Usage (called by train_ai.bat):
  python train_classifier.py --samples 500 --epochs 50 --pause-every 10 --mode fresh
  python train_classifier.py --samples 300 --epochs 30 --pause-every 10 --mode add
"""

import argparse
import base64
import cv2
import numpy as np
import os
import random
import shutil
import sys
import threading
import time
import torch
import torch.nn as nn
import torch.optim as optim
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from torch.utils.data import Dataset, DataLoader
from model import DifferenceClassifier

# ── External Camera Support ──
external_frame = None
external_lock = threading.Lock()
app = FastAPI()

@app.websocket("/ws/external-camera")
async def external_camera_ws(websocket: WebSocket):
    global external_frame
    await websocket.accept()
    print("\n[EXT-CAM] Remote camera connected!")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                data += "=" * ((4 - len(data) % 4) % 4)
                jpg_bytes = base64.b64decode(data)
                nparr = np.frombuffer(jpg_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    with external_lock:
                        external_frame = frame
            except Exception as e:
                print(f"[EXT-CAM] decode error: {e}")
    except WebSocketDisconnect:
        print("\n[EXT-CAM] Remote camera disconnected.")

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")

# ── Config ──
PATCH_SIZE = 32
DATA_DIR = "classifier_training_data"
CLASS_NORMAL = os.path.join(DATA_DIR, "normal")    # class 0 (benign)
CLASS_ANOMALY = os.path.join(DATA_DIR, "anomaly")   # class 1 (synthetic)
MODEL_SAVE_PATH = "classifier_weights.pth"


# ═══════════════════════════════════════════════════════
#  PHASE 1: CAPTURE NORMAL PATCHES FROM WEBCAM
# ═══════════════════════════════════════════════════════

def capture_normal_patches(num_samples=500, source="built_in"):
    """Open webcam, wait 5s countdown, then capture normal scene patches."""
    print("\n" + "=" * 60)
    print("  PHASE 1: CAPTURING NORMAL ENVIRONMENT")
    print("=" * 60)

    cap = None
    if source == "external":
        print("[CAMERA] Waiting for remote camera connection on port 8000...")
        print("[CAMERA] Ensure the main PARALLAX backend is STOPPED.")
        while True:
            with external_lock:
                if external_frame is not None:
                    break
            time.sleep(0.1)
        print("[CAMERA] Remote camera stream active!")
    else:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            print("[ERROR] Cannot open webcam!")
            return False
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # ── 5-second countdown ──
    print("[CAMERA] Camera ready. Position camera at your scene.")
    print("[CAMERA] Capturing starts in 5 seconds...\n")
    countdown_start = time.time()

    while (time.time() - countdown_start) < 5.0:
        if source == "external":
            with external_lock:
                if external_frame is None:
                    time.sleep(0.01)
                    continue
                frame = external_frame.copy()
        else:
            ret, frame = cap.read()
            if not ret:
                continue

        remaining = 5.0 - (time.time() - countdown_start)
        cv2.putText(frame, f"GET READY: {int(remaining) + 1}s",
                     (150, 250), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 255), 4)
        cv2.putText(frame, "Position camera at your scene",
                     (80, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        cv2.imshow("PARALLAX - Training Capture", frame)
        cv2.waitKey(1)

    # ── Capture phase ──
    print(f"[CAPTURE] Now capturing {num_samples} normal patches. Hold still!")
    print("[CAPTURE] Press 'q' to stop early.\n")

    os.makedirs(CLASS_NORMAL, exist_ok=True)

    # Count existing samples (for ADD mode)
    existing = len([f for f in os.listdir(CLASS_NORMAL) if f.endswith('.jpg')]) if os.path.isdir(CLASS_NORMAL) else 0
    captured = 0
    frames_collected = []
    sample_interval = 0.1  # 10 FPS sampling
    last_sample = 0

    while captured < num_samples:
        if source == "external":
            with external_lock:
                if external_frame is None:
                    time.sleep(0.01)
                    continue
                frame = external_frame.copy()
        else:
            ret, frame = cap.read()
            if not ret:
                continue

        now = time.time()
        if (now - last_sample) >= sample_interval:
            # Capture color patches (BGR)
            h, w = frame.shape[:2]

            # Extract random patches from the frame
            for _ in range(3):  # 3 patches per sampled frame
                if captured >= num_samples:
                    break
                py = random.randint(0, h - PATCH_SIZE)
                px = random.randint(0, w - PATCH_SIZE)
                patch = frame[py:py + PATCH_SIZE, px:px + PATCH_SIZE]
                idx = existing + captured
                cv2.imwrite(os.path.join(CLASS_NORMAL, f"normal_{idx:05d}.jpg"), patch)
                captured += 1

            frames_collected.append(frame.copy())
            last_sample = now

        # Display progress
        progress = captured / num_samples
        bar_len = 30
        bar = "=" * int(progress * bar_len) + "-" * (bar_len - int(progress * bar_len))
        cv2.putText(frame, f"CAPTURING: [{bar}] {captured}/{num_samples}",
                     (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.imshow("PARALLAX - Training Capture", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print(f"[CAPTURE] Stopped early at {captured} samples.")
            break

    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()

    if captured < 10:
        print("[ERROR] Not enough patches captured (need at least 10).")
        return False

    print(f"[CAPTURE] Done! {captured} normal patches saved.")
    print(f"[CAPTURE] Total normal samples in dataset: {existing + captured}")

    # ── Generate synthetic anomaly patches ──
    _generate_anomalies(existing + captured)
    return True


def _generate_anomalies(num_to_match):
    """Generate synthetic anomaly patches to match the number of normal samples."""
    print(f"\n[SYNTH] Generating {num_to_match} synthetic ANOMALY patches...")
    os.makedirs(CLASS_ANOMALY, exist_ok=True)

    # Clear old anomalies and regenerate (they should always match normals)
    for f in os.listdir(CLASS_ANOMALY):
        os.remove(os.path.join(CLASS_ANOMALY, f))

    # Load all normal patches as source material
    normal_patches = []
    for fname in os.listdir(CLASS_NORMAL):
        if fname.endswith('.jpg'):
            img = cv2.imread(os.path.join(CLASS_NORMAL, fname))
            if img is not None:
                normal_patches.append(img)

    if len(normal_patches) == 0:
        print("[ERROR] No normal patches to create anomalies from!")
        return

    for i in range(num_to_match):
        base = random.choice(normal_patches).copy().astype(np.float32)
        aug = random.randint(0, 5)

        if aug == 0:
            # Foreign colored rectangle (object placed)
            color = [random.randint(0, 255) for _ in range(3)]
            x1, y1 = random.randint(0, 10), random.randint(0, 10)
            x2, y2 = random.randint(16, 31), random.randint(16, 31)
            base[y1:y2, x1:x2] = color
        elif aug == 1:
            # Edge intrusion with a random color
            t = random.randint(6, 16)
            color = [random.randint(0, 255) for _ in range(3)]
            side = random.randint(0, 3)
            if side == 0: base[:t, :] = color
            elif side == 1: base[-t:, :] = color
            elif side == 2: base[:, :t] = color
            else: base[:, -t:] = color
        elif aug == 2:
            # Random color texture blob
            cx, cy = random.randint(6, 26), random.randint(6, 26)
            r = random.randint(5, 14)
            mask = np.zeros((PATCH_SIZE, PATCH_SIZE), dtype=np.float32)
            cv2.circle(mask, (cx, cy), r, 1.0, -1)
            noise = np.random.randint(0, 256, (PATCH_SIZE, PATCH_SIZE, 3)).astype(np.float32)
            m = mask[:, :, np.newaxis]  # Expand for 3 channels
            base = base * (1 - m) + noise * m
        elif aug == 3:
            # Complete replacement (totally foreign colored object)
            base = np.random.randint(0, 256, (PATCH_SIZE, PATCH_SIZE, 3)).astype(np.float32)
        elif aug == 4:
            # Half color inversion
            if random.randint(0, 1) == 0:
                base[:16, :] = 255 - base[:16, :]
            else:
                base[:, :16] = 255 - base[:, :16]
        else:
            # Paste foreign patch from different region with color shift
            donor = random.choice(normal_patches)
            dy, dx = random.randint(0, 16), random.randint(0, 16)
            size = random.randint(10, 20)
            sy, sx = min(dy, PATCH_SIZE - size), min(dx, PATCH_SIZE - size)
            base[sy:sy+size, sx:sx+size] = donor[sy:sy+size, sx:sx+size] * 0.3 + random.randint(50, 200) * 0.7

        result = np.clip(base, 0, 255).astype(np.uint8)
        cv2.imwrite(os.path.join(CLASS_ANOMALY, f"anomaly_{i:05d}.jpg"), result)

    print(f"[SYNTH] Done! {num_to_match} anomaly patches generated.")


# ═══════════════════════════════════════════════════════
#  PHASE 2: DATASET & TRAINING
# ═══════════════════════════════════════════════════════

class PatchDataset(Dataset):
    def __init__(self):
        self.samples = []
        if os.path.isdir(CLASS_NORMAL):
            for fname in os.listdir(CLASS_NORMAL):
                if fname.endswith(('.jpg', '.png')):
                    self.samples.append((os.path.join(CLASS_NORMAL, fname), 0.0))
        if os.path.isdir(CLASS_ANOMALY):
            for fname in os.listdir(CLASS_ANOMALY):
                if fname.endswith(('.jpg', '.png')):
                    self.samples.append((os.path.join(CLASS_ANOMALY, fname), 1.0))
        random.shuffle(self.samples)

        n_normal = sum(1 for _, l in self.samples if l == 0.0)
        n_anomaly = sum(1 for _, l in self.samples if l == 1.0)
        print(f"[DATASET] {len(self.samples)} total ({n_normal} normal + {n_anomaly} anomaly)")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = cv2.imread(path)  # Read as color BGR
        if img is None:
            img = np.zeros((PATCH_SIZE, PATCH_SIZE, 3), dtype=np.uint8)
        img = cv2.resize(img, (PATCH_SIZE, PATCH_SIZE))
        # BGR -> RGB, normalize, HWC -> CHW
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(img.astype(np.float32) / 255.0).permute(2, 0, 1)
        return tensor, torch.tensor([label], dtype=torch.float32)


def train(epochs=50, batch_size=64, lr=0.001, pause_every=10, resume_weights=False):
    """Train with periodic pause for user review."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n{'=' * 60}")
    print(f"  PHASE 2: TRAINING (Device: {str(device).upper()})")
    print(f"  Epochs: {epochs} | Batch: {batch_size} | LR: {lr}")
    print(f"  Pause every {pause_every} epochs for review")
    print(f"{'=' * 60}\n")

    if str(device) == "cpu":
        print("[WARNING] CUDA not detected. Training on CPU (slower).")
        print("[TIP] Make sure you have torch with CUDA support installed:")
        print("      pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121\n")

    dataset = PatchDataset()
    if len(dataset) == 0:
        print("[ERROR] No training data found!")
        return None

    # 80/20 split
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_set, val_set = torch.utils.data.random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False, num_workers=0)

    model = DifferenceClassifier().to(device)

    # Load existing weights if resuming
    if resume_weights and os.path.isfile(MODEL_SAVE_PATH):
        model.load_state_dict(torch.load(MODEL_SAVE_PATH, map_location=device, weights_only=True))
        print("[TRAIN] Loaded existing model weights for continued training.")

    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=15, gamma=0.5)

    best_val_acc = 0.0

    for epoch in range(1, epochs + 1):
        # ── Train ──
        model.train()
        train_loss = 0.0
        correct = 0
        total = 0

        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            preds = model(batch_x)
            loss = criterion(preds, batch_y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * batch_x.size(0)
            predicted = (preds > 0.5).float()
            correct += (predicted == batch_y).sum().item()
            total += batch_y.size(0)

        train_acc = correct / total
        train_loss /= total

        # ── Validate ──
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        tp = fp = tn = fn = 0

        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                preds = model(batch_x)
                loss = criterion(preds, batch_y)
                val_loss += loss.item() * batch_x.size(0)
                predicted = (preds > 0.5).float()
                val_correct += (predicted == batch_y).sum().item()
                val_total += batch_y.size(0)
                # Confusion matrix
                tp += ((predicted == 1) & (batch_y == 1)).sum().item()
                fp += ((predicted == 1) & (batch_y == 0)).sum().item()
                tn += ((predicted == 0) & (batch_y == 0)).sum().item()
                fn += ((predicted == 0) & (batch_y == 1)).sum().item()

        val_acc = val_correct / max(val_total, 1)
        val_loss /= max(val_total, 1)
        scheduler.step()

        # Progress bar
        bar = "█" * int(train_acc * 20) + "░" * (20 - int(train_acc * 20))
        print(f"  Epoch {epoch:3d}/{epochs} | Loss: {train_loss:.4f} | Acc: {train_acc:.3f} [{bar}] | Val: {val_acc:.3f}")

        # Save best
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), MODEL_SAVE_PATH)

        # ── PAUSE EVERY N EPOCHS ──
        if epoch % pause_every == 0 and epoch < epochs:
            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            f1 = 2 * precision * recall / max(precision + recall, 1e-6)

            print(f"\n{'─' * 60}")
            print(f"  CHECKPOINT at Epoch {epoch}/{epochs}")
            print(f"  ┌─────────────────────────────────────┐")
            print(f"  │ Train Accuracy:  {train_acc:.1%}              │")
            print(f"  │ Val Accuracy:    {val_acc:.1%}              │")
            print(f"  │ Val Loss:        {val_loss:.4f}            │")
            print(f"  │ Precision:       {precision:.1%}              │")
            print(f"  │ Recall:          {recall:.1%}              │")
            print(f"  │ F1 Score:        {f1:.3f}              │")
            print(f"  │ Best Val Acc:    {best_val_acc:.1%}              │")
            print(f"  │                                     │")
            print(f"  │  TP={int(tp):4d}  FP={int(fp):4d}              │")
            print(f"  │  FN={int(fn):4d}  TN={int(tn):4d}              │")
            print(f"  └─────────────────────────────────────┘")
            print(f"  Model auto-saved to: {MODEL_SAVE_PATH}")
            print(f"{'─' * 60}")

            choice = input("\n  [C]ontinue training / [S]top here? (c/s): ").strip().lower()
            if choice == 's':
                print(f"\n[TRAIN] Stopped by user at epoch {epoch}.")
                break
            print(f"  Continuing training...\n")

    # ── Final Report ──
    print(f"\n{'=' * 60}")
    print(f"  TRAINING COMPLETE")
    print(f"  Best Validation Accuracy: {best_val_acc:.1%}")
    print(f"  Model saved to: {MODEL_SAVE_PATH}")
    print(f"{'=' * 60}\n")
    return model


# ═══════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PARALLAX Classifier Training")
    parser.add_argument("--samples", type=int, default=500, help="Normal patches to capture")
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--pause-every", type=int, default=10, help="Pause every N epochs")
    parser.add_argument("--mode", choices=["fresh", "add", "capture-only", "train-only"],
                        default="fresh", help="fresh=new, add=append, capture-only, train-only")
    parser.add_argument("--source", choices=["built_in", "external"],
                        default="built_in", help="built_in=webcam, external=phone remote camera")
    args = parser.parse_args()

    print("=" * 60)
    print("  PARALLAX — DifferenceClassifier Training Pipeline")
    print("  One-Class Learning: Normal scene → everything else = anomaly")
    print(f"  Camera Source: {args.source.upper()}")
    print("=" * 60)

    # Start the external camera server if requested and we are capturing
    if args.source == "external" and args.mode in ["fresh", "add", "capture-only"]:
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        print("\n[SERVER] Started background WebSocket server on port 8000")

    resume_weights = False

    if args.mode == "fresh":
        # Fresh start: delete old data
        if os.path.isdir(DATA_DIR):
            shutil.rmtree(DATA_DIR)
            print("[RESET] Cleared all previous training data.")
        if os.path.isfile(MODEL_SAVE_PATH):
            os.remove(MODEL_SAVE_PATH)
            print("[RESET] Cleared previous model weights.")
        success = capture_normal_patches(args.samples, args.source)
        if not success:
            sys.exit(1)
        # Ask user to confirm before training
        print(f"\n  Captured data ready. Normal: {len(os.listdir(CLASS_NORMAL))} | Anomaly: {len(os.listdir(CLASS_ANOMALY))}")
        confirm = input("  Start training? (y/n): ").strip().lower()
        if confirm != 'y':
            print("  Training cancelled. Data preserved for later.")
            sys.exit(0)
        train(args.epochs, args.batch_size, args.lr, args.pause_every, resume_weights=False)

    elif args.mode == "add":
        # Add more data to existing training set
        resume_weights = True
        success = capture_normal_patches(args.samples, args.source)
        if not success:
            sys.exit(1)
        print(f"\n  Updated data. Normal: {len(os.listdir(CLASS_NORMAL))} | Anomaly: {len(os.listdir(CLASS_ANOMALY))}")
        confirm = input("  Start training with combined data? (y/n): ").strip().lower()
        if confirm != 'y':
            print("  Training cancelled. Data preserved.")
            sys.exit(0)
        train(args.epochs, args.batch_size, args.lr, args.pause_every, resume_weights=True)

    elif args.mode == "capture-only":
        capture_normal_patches(args.samples, args.source)
        print("  Capture complete. Run with --mode train-only to train.")

    elif args.mode == "train-only":
        if not os.path.isdir(CLASS_NORMAL):
            print("[ERROR] No training data. Run capture first.")
            sys.exit(1)
        train(args.epochs, args.batch_size, args.lr, args.pause_every, resume_weights=os.path.isfile(MODEL_SAVE_PATH))
