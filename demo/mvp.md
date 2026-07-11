**PARALLAX (Vision-Only) — MVP SPECIFICATION**

**1. Objective**



**Build a real-time vision-based anomaly detection system that:**



**Learns a baseline representation of a static environment**

**Continuously monitors the scene**

**Computes a probability score indicating deviation from normal**

**Highlights regions contributing to the anomaly**

**Updates dynamically as the scene changes**



**This MVP must visually demonstrate anomaly inference, not object recognition.**



**2. System Scope (Strict Constraints)**

**Included:**

**Single RGB camera input (webcam or phone feed)**

**Real-time processing**

**Statistical + lightweight AI-based anomaly inference**

**Visual overlay + probability score**

**Excluded:**

**Thermal sensing**

**RF sensing**

**Heavy deep learning models (unless lightweight and fast)**

**Cloud processing (keep it local)**

**3. Functional Requirements**

**3.1 Baseline Learning Phase**



**The system must:**



**Capture a sequence of frames (recommended: 50–150 frames over \~5 seconds)**

**Preprocess each frame**

**Construct a baseline model representing “normal”**

**Output:**

**Internal baseline representation (not displayed)**

**Status: “LEARNING BASELINE”**

**3.2 Real-Time Monitoring Phase**



**For every incoming frame:**



**Preprocess frame**

**Compare against baseline**

**Compute deviation metrics**

**Convert deviation → anomaly probability**

**Identify spatial regions contributing to deviation**

**Render output**

**3.3 Output Requirements**



**Display must include:**



**A. Live Video Feed**

**Real-time camera stream**

**B. Anomaly Overlay**

**Highlight regions (bounding boxes or heatmap)**

**C. Probability Score**

**Numeric value: 0.00 → 1.00**

**D. Status Label**

**NORMAL (0.0–0.3)**

**SUSPICIOUS (0.3–0.6)**

**ANOMALY (0.6–1.0)**

**4. Data Pipeline**

**4.1 Frame Acquisition**

**Capture frames at \~15–30 FPS**

**Resolution: 480p or 720p (tradeoff: performance vs clarity)**

**4.2 Preprocessing**



**Each frame must undergo:**



**Convert to grayscale**

**Apply Gaussian blur (reduce noise)**

**Normalize intensity (optional but recommended)**

**4.3 Baseline Model Construction**



**Instead of a single frame:**



**Use statistical aggregation:**

**Mean frame (pixel-wise average)**

**Optional: variance map**

**Result:**

**baseline\_mean**

**baseline\_variance (optional enhancement)**

**5. Feature Extraction Strategy**



**The system should compute multi-factor deviation, not just raw pixel difference.**



**5.1 Pixel Intensity Difference**

**Absolute difference from baseline**

**5.2 Structural Difference**

**Edge detection (e.g., Canny)**

**Compare edge maps with baseline**

**5.3 Texture Disturbance (optional but valuable)**

**Local variance / simple texture metrics**

**6. Deviation Computation**



**For each frame:**



**Compute:**

**diff\_intensity = |current - baseline\_mean|**

**diff\_edges = |edges\_current - edges\_baseline|**

**Combine:**

**Weighted sum of differences**



**Example:**



**deviation\_map = w1 \* diff\_intensity + w2 \* diff\_edges**



**Where:**



**w1 ≈ 0.6**

**w2 ≈ 0.4**

**7. Noise Filtering**



**To avoid false positives:**



**Apply thresholding to deviation map**

**Remove small regions (area threshold)**



**Only consider regions where:**



**Area > predefined threshold (e.g., 300–800 pixels)**

**8. Spatial Localization**

**Extract contours from thresholded deviation**

**For each valid contour:**

**Compute bounding box**

**Mark as anomaly region**

**9. Probability Modeling**



**This is critical for your “AI-like” behavior.**



**9.1 Global Anomaly Score**



**Compute:**



**Mean deviation across frame**

**OR sum of deviation normalized by image size**



**Example conceptual formula:**



**score = total\_deviation / max\_possible\_deviation**



**Normalize to:**



**0 ≤ score ≤ 1**

**9.2 Temporal Smoothing (IMPORTANT)**



**To make it feel intelligent:**



**Maintain rolling average over last N frames (e.g., 5–10)**



**This avoids jittery output.**



**9.3 Classification Mapping**

**Score Range	Label**

**0.0–0.3	NORMAL**

**0.3–0.6	SUSPICIOUS**

**0.6–1.0	ANOMALY**

**10. Visualization Layer**

**10.1 Overlay Options**

**Option A (simplest):**

**Bounding boxes around anomaly regions**

**Option B (better):**

**Heatmap overlay (red intensity = deviation strength)**

**10.2 UI Elements**



**Must display:**



**Status text (top-left)**

**Probability score (top-right)**

**Optional: “Baseline locked” indicator**

**11. Demo Behavior Requirements**



**The system must clearly show:**



**Phase 1 — Stable Scene**

**Score low (\~0.05–0.15)**

**No highlighted regions**

**Phase 2 — Object Introduced**

**Gradual score increase**

**Region highlighted**

**Phase 3 — Object Removed**

**Score returns to baseline**

**12. Demo Scenario Design (Mandatory)**

**Setup:**

**Static camera**

**Table with:**

**Bottle**

**Paper**

**Trigger:**

**Introduce object:**

**Pen behind bottle (partially visible)**

**OR new object in empty space**

**Expected Result:**

**Camera looks mostly unchanged**

**System detects anomaly region**

**Score spikes**

**13. Performance Constraints**

**Must run in real-time on a standard laptop**

**Latency < 200 ms per frame**

**Stable output (no flickering)**

**14. Failure Handling**



**System should:**



**Ignore small lighting fluctuations**

**Ignore tiny motion noise**

**Not trigger on minor camera noise**

**15. Optional Enhancements (If Time Permits)**

**Adaptive baseline update (slow learning)**

**Region-based scoring instead of global only**

**Graph of anomaly score over time**

**16. Deliverable Expectations for AI Agent**



**The generated system should:**



**Be runnable locally with minimal setup**

**Use common libraries (OpenCV, NumPy, etc.)**

**Provide a single-window UI showing all outputs**

**Require no external dataset**

**17. Final Definition of MVP**



**If the system can:**



**✔ Learn baseline**

**✔ Detect a newly introduced object**

**✔ Highlight it**

**✔ Output a probability score**

**✔ Recover after removal**



**Then your MVP is complete and demo-ready**

