import cv2
import time
import threading
import asyncio
import base64
import json
import os
import shutil
import glob
import queue
import numpy as np
from collections import deque
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
import sqlite3
from auth import get_current_user, get_current_user_query, create_access_token, get_password_hash, verify_password, DB_PATH
import torch

from anomaly_detector import ParallaxAI

app = FastAPI(title="PARALLAX Local Backend")

# ── Auth Endpoints ──
@app.post("/auth/signup")
def signup(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (form_data.username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username already registered")
        
    hashed_pw = get_password_hash(form_data.password)
    cursor.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", (form_data.username, hashed_pw))
    conn.commit()
    conn.close()
    return {"msg": "User created successfully"}

@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT hashed_password FROM users WHERE username = ?", (form_data.username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(form_data.password, user[0]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
        
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

# Enable CORS for the React Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Configuration ──
# ── Configuration ──
ring_buffer_seconds = 10       # Pre-anomaly footage buffer (configurable)
post_anomaly_seconds = 15     # Post-anomaly recording (configurable)
record_full_sessions = False   # Keep session video even if no anomalies
ANOMALY_STORAGE_ROOT = "anomaly_storage"
THUMBNAIL_QUALITY = 90
VIDEO_CODEC = "avc1"
VIDEO_EXT = ".mp4"
COOLDOWN_SECONDS = 10          # Min gap between anomaly events
RETENTION_DAYS = 30            # Auto-cleanup: delete data older than this
SESSION_VIDEO_FPS = 10         # Full session recording at lower FPS to save disk
SESSION_VIDEO_INTERVAL = 3     # Write every Nth frame to session video (saves ~66% disk)
calibration_delay_seconds = 5.0    # Buffer delay before calibration starts
calibration_duration_seconds = 10.0 # Model training duration before inference starts
auto_recalibrate_minutes = 0       # Interval to reset baseline (0 = disabled)

# Thread-safe globals
processing_thread = None
is_processing = threading.Event()
latest_payload = None
current_session_id = None
feedback_queue = queue.Queue()

anomaly_history = []
anomaly_history_lock = threading.Lock()

# ── External Camera Support ──
external_camera_frame = None
external_camera_lock = threading.Lock()
external_camera_connected = False
use_external_camera = False  # Toggle: True = external, False = built-in

# Ensure storage root exists
os.makedirs(ANOMALY_STORAGE_ROOT, exist_ok=True)


# ═══════════════════════════════════════════════════════
#  AUTO-CLEANUP JOB
# ═══════════════════════════════════════════════════════

def _run_cleanup():
    """Delete session folders older than RETENTION_DAYS. Runs on app startup and daily."""
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    deleted = 0
    if not os.path.isdir(ANOMALY_STORAGE_ROOT):
        return

    for session_name in os.listdir(ANOMALY_STORAGE_ROOT):
        session_path = os.path.join(ANOMALY_STORAGE_ROOT, session_name)
        if not os.path.isdir(session_path):
            continue
        try:
            # Session folders are named like 20260425_194500
            session_date = datetime.strptime(session_name, "%Y%m%d_%H%M%S")
            if session_date < cutoff:
                shutil.rmtree(session_path)
                deleted += 1
                print(f"[CLEANUP] Deleted expired session: {session_name}")
        except ValueError:
            continue  # Skip folders that don't match the naming convention

    if deleted:
        print(f"[CLEANUP] Purged {deleted} session(s) older than {RETENTION_DAYS} days.")
    else:
        print(f"[CLEANUP] No expired sessions found (retention: {RETENTION_DAYS} days).")


async def _cleanup_scheduler():
    """Background task that runs cleanup once a day."""
    while True:
        _run_cleanup()
        await asyncio.sleep(86400)  # 24 hours


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(_cleanup_scheduler())
    # Purge all existing false_positive data on startup
    _purge_all_filtered()


# ═══════════════════════════════════════════════════════
#  ANOMALY CLIP WRITER (background thread)
# ═══════════════════════════════════════════════════════

def _save_anomaly_clip(frames, fps, session_dir, anomaly_id, trigger_frame, score, start_ts, end_ts):
    """Background thread: writes clip, thumbnail, and metadata to disk."""
    anomaly_dir = os.path.join(session_dir, anomaly_id)
    os.makedirs(anomaly_dir, exist_ok=True)

    # 1. Video Clip
    clip_path = os.path.join(anomaly_dir, f"clip{VIDEO_EXT}")
    h, w = frames[0].shape[:2]
    writer_fps = max(int(fps), 15)
    fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
    writer = cv2.VideoWriter(clip_path, fourcc, writer_fps, (w, h))
    for f in frames:
        writer.write(f)
    writer.release()

    # 2. Thumbnail
    thumb_path = os.path.join(anomaly_dir, "thumbnail.jpg")
    cv2.imwrite(thumb_path, trigger_frame, [int(cv2.IMWRITE_JPEG_QUALITY), THUMBNAIL_QUALITY])

    # 3. Metadata JSON
    meta = {
        "anomaly_id": anomaly_id,
        "session_id": os.path.basename(session_dir),
        "start_time": start_ts,
        "start_time_human": datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": end_ts,
        "duration_seconds": round(end_ts - start_ts, 2),
        "peak_score": round(float(score), 6),
        "frame_count": len(frames),
        "resolution": f"{w}x{h}",
        "clip_file": f"clip{VIDEO_EXT}",
        "thumbnail_file": "thumbnail.jpg",
        "status": "anomaly"
    }
    meta_path = os.path.join(anomaly_dir, "metadata.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    with anomaly_history_lock:
        anomaly_history.append(meta)

    clip_size_mb = os.path.getsize(clip_path) / (1024 * 1024)
    print(f"[PERSIST] Anomaly saved → {anomaly_dir}  |  {len(frames)} frames  |  {clip_size_mb:.1f} MB")


# ═══════════════════════════════════════════════════════
#  SESSION METADATA WRITER
# ═══════════════════════════════════════════════════════

def _write_session_meta(session_dir, session_id, start_ts, end_ts, anomaly_count, total_frames):
    """Write session-level metadata JSON when processing stops."""
    meta = {
        "session_id": session_id,
        "start_time": start_ts,
        "start_time_human": datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": end_ts,
        "end_time_human": datetime.fromtimestamp(end_ts).strftime("%Y-%m-%d %H:%M:%S"),
        "duration_seconds": round(end_ts - start_ts, 2),
        "anomaly_count": anomaly_count,
        "total_frames_processed": total_frames,
    }
    meta_path = os.path.join(session_dir, "session_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[SESSION] Metadata written → {meta_path}")


# ═══════════════════════════════════════════════════════
#  MAIN PROCESSING LOOP
# ═══════════════════════════════════════════════════════

def processing_loop():
    global latest_payload, current_session_id
    print("[BACKEND] Processing loop started. Initializing AI Engine...")

    ai = ParallaxAI()
    ai.state = "INFER"
    print(f"[BACKEND] AI Engine initialized on device: {ai.device.type.upper()}")

    # Pre-warm model
    _ = ai.model(torch.zeros(1, 3, 128, 128).to(ai.device))

    # ── Camera source: built-in or external ──
    cap = None
    if not use_external_camera:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FPS, 60)
        if not cap.isOpened():
            print("[BACKEND] Warning: Camera could not be opened.")
    else:
        print("[BACKEND] Using EXTERNAL camera source. Waiting for frames...")

    # ── Session setup ──
    current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = os.path.join(ANOMALY_STORAGE_ROOT, current_session_id)
    os.makedirs(session_dir, exist_ok=True)
    print(f"[BACKEND] Session: {current_session_id}")

    with anomaly_history_lock:
        anomaly_history.clear()

    # ── Session-level video recorder ──
    session_video_path = os.path.join(session_dir, f"session_full{VIDEO_EXT}")
    session_writer = None
    session_frame_counter = 0

    prev_time = time.time()
    session_start_time = time.time()
    last_recalibration_time = session_start_time
    total_frames = 0

    # ── Ring buffer ──
    ring_buffer = deque(maxlen=1)

    # ── Anomaly state machine ──
    anomaly_active = False
    anomaly_start_time = 0.0
    anomaly_peak_score = 0.0
    anomaly_trigger_frame = None
    anomaly_post_frames = []
    post_capture_end_time = 0.0
    last_anomaly_save_time = 0.0
    anomaly_count = 0

    consecutive_failures = 0
    while is_processing.is_set():
        frame = None
        got_frame = False

        if use_external_camera:
            # Read from the external camera buffer
            with external_camera_lock:
                if external_camera_frame is not None:
                    frame = external_camera_frame.copy()
                    got_frame = True
            if not got_frame:
                time.sleep(0.01)
                continue
        else:
            # Read from built-in camera
            if cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    consecutive_failures += 1
                    if consecutive_failures > 30:
                        print("[BACKEND] Too many frame failures. Reopening camera...")
                        cap.release()
                        time.sleep(1)
                        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                        cap.set(cv2.CAP_PROP_FPS, 60)
                        consecutive_failures = 0
                    time.sleep(0.01)
                    continue
                got_frame = True
                consecutive_failures = 0
            else:
                time.sleep(0.016)
                continue

        if not got_frame or frame is None:
            time.sleep(0.01)
            continue

        now = time.time()
        fps = 1.0 / max(now - prev_time, 1e-6)
        prev_time = now
        total_frames += 1

        # ── Session video: write every Nth frame at lower FPS ──
        if record_full_sessions:
            session_frame_counter += 1
            if session_writer is None:
                h, w = frame.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
                session_writer = cv2.VideoWriter(session_video_path, fourcc, SESSION_VIDEO_FPS, (w, h))
            if session_frame_counter % SESSION_VIDEO_INTERVAL == 0:
                session_writer.write(frame)

        # ── Ring buffer sizing ──
        target_ring_size = int(ring_buffer_seconds * max(fps, 15))
        if ring_buffer.maxlen != target_ring_size:
            ring_buffer = deque(ring_buffer, maxlen=target_ring_size)
        ring_buffer.append(frame.copy())

        # ── AI WARMUP OR INFERENCE ──
        display = frame.copy()
        tensor_frame = ai.preprocess_for_ai(frame).to(ai.device)
        is_anomalous = False
        is_warming_up = False
        best_crop = None
        patch_b64 = None

        # ── Auto Recalibration Check ──
        if auto_recalibrate_minutes > 0:
            if (now - last_recalibration_time) > (auto_recalibrate_minutes * 60):
                print(f"[BACKEND] Auto-recalibration triggered ({auto_recalibrate_minutes}m elapsed).")
                from model import ConvAutoencoder
                import torch.optim as optim
                ai.model = ConvAutoencoder().to(ai.device)
                ai.optimizer = optim.Adam(ai.model.parameters(), lr=0.002)
                last_recalibration_time = now
                ai.smooth_score = 0.0

        time_since_recal = now - last_recalibration_time
        
        if time_since_recal < calibration_delay_seconds:
            is_warming_up = True
            ai.model.eval() # Just wait, no training
            cv2.putText(display, f"WAITING FOR CALIBRATION: {int(calibration_delay_seconds - time_since_recal)}s", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 165, 255), 3)
        elif time_since_recal < (calibration_delay_seconds + calibration_duration_seconds):
            is_warming_up = True
            # Online training (Warmup Phase)
            ai.model.train()
            for _ in range(2): # Quick online training passes
                ai.optimizer.zero_grad()
                reconstructed = ai.model(tensor_frame)
                loss = torch.nn.functional.mse_loss(reconstructed, tensor_frame)
                loss.backward()
                ai.optimizer.step()
            
            ai.smooth_score = loss.item()
            calib_elapsed = time_since_recal - calibration_delay_seconds
            cv2.putText(display, f"CALIBRATING AI: {int(calib_elapsed)}/{int(calibration_duration_seconds)}s", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
        else:
            # Inference Phase
            ai.model.eval()
            with torch.no_grad():
                reconstructed = ai.model(tensor_frame)
                loss_map_tensor = ai.criterion(reconstructed, tensor_frame)
                # Average across 3 color channels to get single-channel anomaly heatmap
                loss_map_raw = loss_map_tensor.squeeze().mean(dim=0).cpu().numpy()

            max_frame_error = loss_map_raw.max()
            ai.smooth_score = (ai.smooth_score * 0.9) + (max_frame_error * 0.1)


            loss_map_visual = (loss_map_raw * 255.0 * 5.0) 
            loss_map_visual = np.clip(loss_map_visual, 0, 255).astype(np.uint8)
            loss_map_visual = cv2.GaussianBlur(loss_map_visual, (5, 5), 0)
            
            _, binary_anomaly = cv2.threshold(loss_map_visual, 50, 255, cv2.THRESH_BINARY)
            h, w = frame.shape[:2]
            binary_anomaly_large = cv2.resize(binary_anomaly, (w, h), interpolation=cv2.INTER_NEAREST)
            contours, _ = cv2.findContours(binary_anomaly_large, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            # Group nearby anomalies
            kernel_large = cv2.getStructuringElement(cv2.MORPH_RECT, (60, 60))
            grouped_mask = cv2.dilate(binary_anomaly_large, kernel_large)
            grouped_contours, _ = cv2.findContours(grouped_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            active_crops = []
            best_crop = None
            highest_prob = -1.0
            
            last_anomalous_crops = [] # Cache for feedback

            for g_cnt in grouped_contours:
                if cv2.contourArea(g_cnt) > 500: # Filter small noise
                    gx, gy, gbw, gbh = cv2.boundingRect(g_cnt)
                    
                    # Get crop for classifier AND UI (the combined large box)
                    pad = 20
                    gx1 = max(0, gx - pad)
                    gy1 = max(0, gy - pad)
                    gx2 = min(w, gx + gbw + pad)
                    gy2 = min(h, gy + gbh + pad)
                    
                    crop = frame[gy1:gy2, gx1:gx2]
                    if crop.size > 0:
                        crop_tensor = ai.preprocess_for_classifier(crop).to(ai.device)
                        active_crops.append(crop_tensor)
                        last_anomalous_crops.append(crop_tensor)
                        
                        with torch.no_grad():
                            prob_anomaly = ai.classifier(crop_tensor).item()
                            
                        if prob_anomaly > highest_prob:
                            highest_prob = prob_anomaly
                            best_crop = crop
                            
                        # Find all precise original contours that fall within this grouped box
                        inner_contours = []
                        for orig_cnt in contours:
                            ox, oy, obw, obh = cv2.boundingRect(orig_cnt)
                            cx, cy = ox + obw // 2, oy + obh // 2
                            if gx <= cx <= gx + gbw and gy <= cy <= gy + gbh:
                                inner_contours.append(orig_cnt)
                        
                        if prob_anomaly > 0.5:
                            is_anomalous = True
                            # Draw the actual free-form shape of the anomalies inside this group
                            cv2.drawContours(display, inner_contours, -1, (0, 0, 255), 2)
                            cv2.putText(display, f"ANOMALY {prob_anomaly:.2f}", (gx, max(20, gy-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)

            # HANDLE MANUAL FEEDBACK
            if not hasattr(ai, 'optimizer_classifier'):
                ai.optimizer_classifier = torch.optim.Adam(ai.classifier.parameters(), lr=0.001)

            while not feedback_queue.empty():
                label = feedback_queue.get()
                if label == "true_anomaly":
                    if len(last_anomalous_crops) > 0:
                        print("[FEEDBACK] True Anomaly confirmed. Reinforcing classifier.")
                        ai.classifier.eval()  # Use eval to prevent BatchNorm crash with batch_size=1
                        ai.optimizer_classifier.zero_grad()
                        for c_tensor in last_anomalous_crops:
                            pred = ai.classifier(c_tensor)
                            loss_c = torch.nn.functional.binary_cross_entropy(pred, torch.ones_like(pred))
                            loss_c.backward()
                        ai.optimizer_classifier.step()
                    else:
                        print("[FEEDBACK] True Anomaly ignored: No recent crop found.")
                elif label == "false_positive":
                    print("[FEEDBACK] False Positive. Forcing autoencoder to learn baseline.")
                    # False Positive -> Train Autoencoder aggressively to absorb the new baseline
                    ai.model.train() # Autoencoder doesn't use BatchNorm, so train() is fine
                    for param_group in ai.optimizer.param_groups:
                        param_group['lr'] = 0.005
                    for _ in range(15):
                        ai.optimizer.zero_grad()
                        recon = ai.model(tensor_frame)
                        loss_ae = torch.nn.functional.mse_loss(recon, tensor_frame)
                        loss_ae.backward()
                        ai.optimizer.step()
                    for param_group in ai.optimizer.param_groups:
                        param_group['lr'] = 0.002
                    
                    # Also train classifier to reject this crop
                    if len(last_anomalous_crops) > 0:
                        ai.classifier.eval() # Use eval to prevent BatchNorm crash with batch_size=1
                        ai.optimizer_classifier.zero_grad()
                        for c_tensor in last_anomalous_crops:
                            pred = ai.classifier(c_tensor)
                            loss_c = torch.nn.functional.binary_cross_entropy(pred, torch.zeros_like(pred))
                            loss_c.backward()
                        ai.optimizer_classifier.step()

        # ── Anomaly Persistence State Machine ──
        if is_anomalous:
            if not anomaly_active:
                if (now - last_anomaly_save_time) > COOLDOWN_SECONDS and post_capture_end_time == 0.0:
                    anomaly_active = True
                    anomaly_start_time = now
                    anomaly_peak_score = ai.smooth_score
                    anomaly_trigger_frame = frame.copy()
                    anomaly_post_frames = list(ring_buffer)
                    print(f"[PERSIST] Anomaly event STARTED (score: {ai.smooth_score:.4f})")
                elif post_capture_end_time > 0.0:
                    anomaly_active = True
                    post_capture_end_time = 0.0
                    print(f"[PERSIST] Anomaly event RESUMED")

        if anomaly_active:
            anomaly_peak_score = max(anomaly_peak_score, ai.smooth_score)
            if not is_anomalous:
                anomaly_active = False
                post_capture_end_time = now + post_anomaly_seconds
                print(f"[PERSIST] Anomaly ended. Post-capture for {post_anomaly_seconds}s...")
            else:
                anomaly_post_frames.append(frame.copy())
        else:
            if post_capture_end_time > 0:
                if now < post_capture_end_time:
                    anomaly_post_frames.append(frame.copy())
                else:
                    post_capture_end_time = 0.0
                    last_anomaly_save_time = now
                    anomaly_count += 1
                    anomaly_id = f"anomaly_{anomaly_count:04d}_{int(anomaly_start_time)}"
                    all_frames = list(anomaly_post_frames)
                    
                    threading.Thread(
                        target=_save_anomaly_clip,
                        args=(all_frames, fps, session_dir, anomaly_id,
                              anomaly_trigger_frame, anomaly_peak_score,
                              anomaly_start_time, now),
                        daemon=True,
                    ).start()
                    print(f"[PERSIST] Anomaly #{anomaly_count} queued ({len(all_frames)} frames).")
                    anomaly_post_frames = []
                    anomaly_trigger_frame = None

        # ── Stream to WebSocket ──
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
        ret_enc, buffer = cv2.imencode('.jpg', display, encode_param)
        
        patch_b64 = None
        if best_crop is not None and best_crop.size > 0:
            ret_p, buffer_p = cv2.imencode('.jpg', best_crop, encode_param)
            if ret_p:
                patch_b64 = base64.b64encode(buffer_p).decode('utf-8')

        if ret_enc:
            b64_image = base64.b64encode(buffer).decode('utf-8')
            payload = {
                "image": b64_image,
                "metadata": {
                    "is_anomalous": is_anomalous,
                    "warming_up": is_warming_up,
                    "patch_image": patch_b64,
                    "score": float(ai.smooth_score),
                    "fps": int(fps),
                    "session_id": current_session_id,
                    "anomaly_count": anomaly_count,
                    "recording": anomaly_active or post_capture_end_time > 0,
                }
            }
            latest_payload = json.dumps(payload)

    # ── Cleanup on stop ──
    if session_writer is not None:
        session_writer.release()
    if cap is not None and cap.isOpened():
        cap.release()

    _write_session_meta(session_dir, current_session_id,
                        session_start_time, time.time(), anomaly_count, total_frames)

    # ── Auto-delete empty session if configured ──
    if anomaly_count == 0 and not record_full_sessions:
        try:
            import shutil
            shutil.rmtree(session_dir)
            print(f"[BACKEND] Deleted empty session: {current_session_id}")
        except Exception as e:
            print(f"[BACKEND] Failed to delete empty session: {e}")

    latest_payload = None
    print("[BACKEND] Processing loop stopped.")


# ═══════════════════════════════════════════════════════
#  API ENDPOINTS
# ═══════════════════════════════════════════════════════

from pydantic import BaseModel

class Feedback(BaseModel):
    label: str

@app.post("/feedback")
def receive_feedback(payload: Feedback, current_user: str = Depends(get_current_user)):
    feedback_queue.put(payload.label)
    return {"status": "feedback logged"}

@app.post("/start-processing")
def start_processing(current_user: str = Depends(get_current_user)):
    global processing_thread
    if is_processing.is_set():
        return {"status": "already running"}
    is_processing.set()
    processing_thread = threading.Thread(target=processing_loop, daemon=True)
    processing_thread.start()
    return {"status": "started"}


@app.post("/stop-processing")
def stop_processing(current_user: str = Depends(get_current_user)):
    global processing_thread
    if not is_processing.is_set():
        return {"status": "already stopped"}
    is_processing.clear()
    if processing_thread is not None:
        processing_thread.join(timeout=5.0)
        processing_thread = None
    return {"status": "stopped"}


# ── Sessions ──

@app.get("/sessions")
def list_sessions(current_user: str = Depends(get_current_user)):
    """List all recorded sessions, newest first."""
    sessions = []
    if not os.path.isdir(ANOMALY_STORAGE_ROOT):
        return {"sessions": []}

    for name in sorted(os.listdir(ANOMALY_STORAGE_ROOT), reverse=True):
        path = os.path.join(ANOMALY_STORAGE_ROOT, name)
        if not os.path.isdir(path):
            continue

        meta_path = os.path.join(path, "session_meta.json")
        if os.path.isfile(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
        else:
            # Session still running or meta not written yet
            meta = {"session_id": name, "status": "active" if name == current_session_id else "incomplete"}

        # Count anomaly subdirs
        anomaly_dirs = [d for d in os.listdir(path) if d.startswith("anomaly_") and os.path.isdir(os.path.join(path, d))]
        meta["anomaly_count"] = len(anomaly_dirs)
        meta["has_video"] = os.path.isfile(os.path.join(path, f"session_full{VIDEO_EXT}")) or os.path.isfile(os.path.join(path, "session_full.avi"))
        sessions.append(meta)

    return {"sessions": sessions}


@app.get("/sessions/{session_id}")
def get_session(session_id: str, current_user: str = Depends(get_current_user)):
    """Get details for a specific session including its anomalies."""
    session_path = os.path.join(ANOMALY_STORAGE_ROOT, session_id)
    if not os.path.isdir(session_path):
        raise HTTPException(status_code=404, detail="Session not found")

    # Load session meta
    meta_path = os.path.join(session_path, "session_meta.json")
    session_meta = {}
    if os.path.isfile(meta_path):
        with open(meta_path) as f:
            session_meta = json.load(f)
    else:
        session_meta = {"session_id": session_id}

    # Collect anomalies for this session
    anomalies = []
    for name in sorted(os.listdir(session_path)):
        anom_dir = os.path.join(session_path, name)
        if not name.startswith("anomaly_") or not os.path.isdir(anom_dir):
            continue
        anom_meta_path = os.path.join(anom_dir, "metadata.json")
        if os.path.isfile(anom_meta_path):
            with open(anom_meta_path) as f:
                anomalies.append(json.load(f))

    session_meta["anomalies"] = anomalies
    session_meta["has_video"] = os.path.isfile(os.path.join(session_path, f"session_full{VIDEO_EXT}")) or os.path.isfile(os.path.join(session_path, "session_full.avi"))
    return session_meta


@app.get("/sessions/{session_id}/video")
def get_session_video(session_id: str, token: str = None):
    current_user = get_current_user_query(token)
    """Stream the full session video file."""
    # Check for mp4 first, then legacy avi
    video_path = os.path.join(ANOMALY_STORAGE_ROOT, session_id, f"session_full{VIDEO_EXT}")
    if not os.path.isfile(video_path):
        video_path = os.path.join(ANOMALY_STORAGE_ROOT, session_id, "session_full.avi")
    if not os.path.isfile(video_path):
        raise HTTPException(status_code=404, detail="Session video not found")
    ext = os.path.splitext(video_path)[1]
    media = "video/mp4" if ext == ".mp4" else "video/x-msvideo"
    return FileResponse(video_path, media_type=media, filename=f"session_{session_id}{ext}")


# ── Anomalies ──

@app.get("/anomalies")
def get_anomalies(current_user: str = Depends(get_current_user)):
    """Returns the anomaly history for the current session (live)."""
    with anomaly_history_lock:
        return {"session_id": current_session_id, "anomalies": list(anomaly_history)}


@app.get("/anomalies/{session_id}/{anomaly_id}")
def get_anomaly(session_id: str, anomaly_id: str, current_user: str = Depends(get_current_user)):
    """Get metadata for a specific anomaly."""
    meta_path = os.path.join(ANOMALY_STORAGE_ROOT, session_id, anomaly_id, "metadata.json")
    if not os.path.isfile(meta_path):
        raise HTTPException(status_code=404, detail="Anomaly not found")
    with open(meta_path) as f:
        return json.load(f)


@app.get("/anomalies/{session_id}/{anomaly_id}/thumbnail")
def get_anomaly_thumbnail(session_id: str, anomaly_id: str, token: str = None):
    current_user = get_current_user_query(token)
    """Serve the anomaly thumbnail image."""
    thumb_path = os.path.join(ANOMALY_STORAGE_ROOT, session_id, anomaly_id, "thumbnail.jpg")
    if not os.path.isfile(thumb_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(thumb_path, media_type="image/jpeg")


@app.get("/anomalies/{session_id}/{anomaly_id}/clip")
def get_anomaly_clip(session_id: str, anomaly_id: str, token: str = None):
    current_user = get_current_user_query(token)
    """Serve the anomaly video clip."""
    # Check for mp4 first, then legacy formats
    clip_path = os.path.join(ANOMALY_STORAGE_ROOT, session_id, anomaly_id, f"clip{VIDEO_EXT}")
    if not os.path.isfile(clip_path):
        clip_path = os.path.join(ANOMALY_STORAGE_ROOT, session_id, anomaly_id, "clip.webm")
    if not os.path.isfile(clip_path):
        clip_path = os.path.join(ANOMALY_STORAGE_ROOT, session_id, anomaly_id, "clip.avi")
    if not os.path.isfile(clip_path):
        raise HTTPException(status_code=404, detail="Clip not found")
    ext = os.path.splitext(clip_path)[1]
    media = "video/mp4" if ext == ".mp4" else ("video/webm" if ext == ".webm" else "video/x-msvideo")
    return FileResponse(clip_path, media_type=media, filename=f"{anomaly_id}{ext}")


@app.post("/anomalies/{session_id}/{anomaly_id}/status")
async def update_anomaly_status(session_id: str, anomaly_id: str, request: dict, current_user: str = Depends(get_current_user)):
    """Update the status of an anomaly (e.g., to 'false_positive')."""
    meta_path = os.path.join(ANOMALY_STORAGE_ROOT, session_id, anomaly_id, "metadata.json")
    if not os.path.isfile(meta_path):
        raise HTTPException(status_code=404, detail="Anomaly not found")
    
    with open(meta_path, "r") as f:
        meta = json.load(f)
        
    meta["status"] = request.get("status", "anomaly")
    
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
        
    return {"status": "success", "anomaly_status": meta["status"]}


@app.delete("/anomalies/{session_id}/{anomaly_id}")
def delete_anomaly(session_id: str, anomaly_id: str, current_user: str = Depends(get_current_user)):
    """Permanently delete an anomaly folder."""
    anomaly_path = os.path.join(ANOMALY_STORAGE_ROOT, session_id, anomaly_id)
    if not os.path.isdir(anomaly_path):
        raise HTTPException(status_code=404, detail="Anomaly not found")
        
    shutil.rmtree(anomaly_path)
    return {"status": "deleted"}


# ── Cleanup config ──

@app.get("/config/retention")
def get_retention(current_user: str = Depends(get_current_user)):
    return {"retention_days": RETENTION_DAYS}


@app.post("/config/retention/{days}")
def set_retention(days: int, current_user: str = Depends(get_current_user)):
    global RETENTION_DAYS
    if days < 1:
        raise HTTPException(status_code=400, detail="Retention must be at least 1 day")
    RETENTION_DAYS = days
    return {"retention_days": RETENTION_DAYS, "message": f"Retention set to {days} days."}


@app.post("/cleanup/run")
def trigger_cleanup(current_user: str = Depends(get_current_user)):
    """Manually trigger the cleanup job."""
    _run_cleanup()
    return {"status": "cleanup completed", "retention_days": RETENTION_DAYS}


# ── Clip Timing Config ──




# ── Cross-Session Filtered Anomalies ──

def _purge_all_filtered():
    """Delete all anomaly folders with status 'false_positive' across all sessions."""
    if not os.path.isdir(ANOMALY_STORAGE_ROOT):
        return 0
    deleted = 0
    for session_name in os.listdir(ANOMALY_STORAGE_ROOT):
        session_path = os.path.join(ANOMALY_STORAGE_ROOT, session_name)
        if not os.path.isdir(session_path):
            continue
        for anom_name in os.listdir(session_path):
            anom_dir = os.path.join(session_path, anom_name)
            if not anom_name.startswith("anomaly_") or not os.path.isdir(anom_dir):
                continue
            meta_path = os.path.join(anom_dir, "metadata.json")
            if os.path.isfile(meta_path):
                with open(meta_path) as f:
                    meta = json.load(f)
                if meta.get("status") == "false_positive":
                    shutil.rmtree(anom_dir)
                    deleted += 1
    if deleted:
        print(f"[PURGE] Deleted {deleted} false positive anomalies.")
    return deleted


@app.get("/filtered-anomalies")
def list_filtered_anomalies(current_user: str = Depends(get_current_user)):
    """List ALL false_positive anomalies across ALL sessions."""
    filtered = []
    if not os.path.isdir(ANOMALY_STORAGE_ROOT):
        return {"anomalies": []}

    for session_name in sorted(os.listdir(ANOMALY_STORAGE_ROOT), reverse=True):
        session_path = os.path.join(ANOMALY_STORAGE_ROOT, session_name)
        if not os.path.isdir(session_path):
            continue
        for anom_name in sorted(os.listdir(session_path)):
            anom_dir = os.path.join(session_path, anom_name)
            if not anom_name.startswith("anomaly_") or not os.path.isdir(anom_dir):
                continue
            meta_path = os.path.join(anom_dir, "metadata.json")
            if os.path.isfile(meta_path):
                with open(meta_path) as f:
                    meta = json.load(f)
                if meta.get("status") == "false_positive":
                    filtered.append(meta)

    return {"anomalies": filtered}


@app.delete("/filtered-anomalies/purge")
def purge_filtered_anomalies(current_user: str = Depends(get_current_user)):
    """Bulk-delete ALL false_positive anomalies across ALL sessions."""
    deleted = _purge_all_filtered()
    return {"status": "purged", "deleted_count": deleted}

# ── Recording Config ──

@app.get("/config/recording")
def get_recording_config(current_user: str = Depends(get_current_user)):
    return {
        "ring_buffer_seconds": ring_buffer_seconds,
        "post_anomaly_seconds": post_anomaly_seconds,
        "record_full_sessions": record_full_sessions
    }

@app.post("/config/recording")
async def set_recording_config(request: dict, current_user: str = Depends(get_current_user)):
    global ring_buffer_seconds, post_anomaly_seconds, record_full_sessions
    if "ring_buffer_seconds" in request:
        ring_buffer_seconds = int(request["ring_buffer_seconds"])
    if "post_anomaly_seconds" in request:
        post_anomaly_seconds = int(request["post_anomaly_seconds"])
    if "record_full_sessions" in request:
        record_full_sessions = bool(request["record_full_sessions"])
    print(f"[CONFIG] Recording settings updated: pre={ring_buffer_seconds}s, post={post_anomaly_seconds}s, full_session={record_full_sessions}")
    return {"status": "success", "message": "Recording settings updated"}

# ── Autoencoder Config ──

@app.get("/config/autoencoder")
def get_autoencoder_config(current_user: str = Depends(get_current_user)):
    return {
        "calibration_delay_seconds": int(calibration_delay_seconds),
        "calibration_duration_seconds": int(calibration_duration_seconds),
        "auto_recalibrate_minutes": int(auto_recalibrate_minutes)
    }

@app.post("/config/autoencoder")
async def set_autoencoder_config(request: dict, current_user: str = Depends(get_current_user)):
    global calibration_delay_seconds, calibration_duration_seconds, auto_recalibrate_minutes
    if "calibration_delay_seconds" in request:
        calibration_delay_seconds = float(request["calibration_delay_seconds"])
    if "calibration_duration_seconds" in request:
        calibration_duration_seconds = float(request["calibration_duration_seconds"])
    if "auto_recalibrate_minutes" in request:
        auto_recalibrate_minutes = float(request["auto_recalibrate_minutes"])
    print(f"[CONFIG] Autoencoder settings updated: delay={calibration_delay_seconds}s, duration={calibration_duration_seconds}s, auto_reset={auto_recalibrate_minutes}m")
    return {"status": "success", "message": "Autoencoder settings updated"}

# ── External Camera Config ──

@app.get("/config/camera-source")
def get_camera_source(current_user: str = Depends(get_current_user)):
    return {
        "source": "external" if use_external_camera else "built_in",
        "external_connected": external_camera_connected
    }


@app.post("/config/camera-source")
async def set_camera_source(request: dict, current_user: str = Depends(get_current_user)):
    global use_external_camera
    source = request.get("source", "built_in")
    if source not in ("built_in", "external"):
        raise HTTPException(status_code=400, detail="Source must be 'built_in' or 'external'")
    use_external_camera = (source == "external")
    print(f"[CONFIG] Camera source set to: {source.upper()}")
    return {
        "source": source,
        "message": f"Camera source set to {source}. Restart the processing engine to apply."
    }


# ── WebSocket: External Camera Ingest ──

@app.websocket("/ws/external-camera")
async def external_camera_ws(websocket: WebSocket):
    global external_camera_frame, external_camera_connected
    await websocket.accept()
    external_camera_connected = True
    print("[EXT-CAM] Remote camera connected.")
    try:
        while True:
            data = await websocket.receive_text()
            # data is base64-encoded JPEG
            try:
                data += "=" * ((4 - len(data) % 4) % 4)
                jpg_bytes = base64.b64decode(data)
                nparr = np.frombuffer(jpg_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    with external_camera_lock:
                        external_camera_frame = frame
            except Exception as e:
                print(f"[EXT-CAM] Frame decode error: {e}")
    except WebSocketDisconnect:
        pass
    finally:
        external_camera_connected = False
        print("[EXT-CAM] Remote camera disconnected.")


# ── WebSocket: Dashboard ──

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    try:
        current_user = get_current_user_query(token)
    except Exception as e:
        await websocket.close(code=1008)
        return
        
    await websocket.accept()
    print("[BACKEND] Client connected to WebSocket.")
    last_sent = None
    try:
        while True:
            current = latest_payload
            if current is not None and current is not last_sent:
                await websocket.send_text(current)
                last_sent = current
            await asyncio.sleep(1 / 30)  # 30fps max to browser
    except WebSocketDisconnect:
        print("[BACKEND] WebSocket client disconnected.")


@app.get("/")
async def root():
    return {"status": "Backend running. Please load React frontend."}


if __name__ == "__main__":
    import uvicorn
    print("Starting PARALLAX API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
