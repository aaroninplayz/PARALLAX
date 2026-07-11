@echo off
setlocal enabledelayedexpansion
title PARALLAX - AI Classifier Training
color 0A

echo.
echo  ============================================================
echo  ::         PARALLAX -- AI CLASSIFIER TRAINING              ::
echo  ::   Train the anomaly detection brain on YOUR environment  ::
echo  ============================================================
echo.

:: -- Configurable Parameters --
set SAMPLES=500
set EPOCHS=50
set BATCH_SIZE=64
set LEARNING_RATE=0.001
set PAUSE_EVERY=10

:: -- Check for existing trained model --
if exist "classifier_weights.pth" (
    echo  [!] A trained model already exists.
    echo.
    echo  Choose an option:
    echo    [1] ADD     - Capture new environment data and add to existing training
    echo    [2] RESET   - Delete everything and start fresh
    echo    [3] RETRAIN - Retrain on existing data without new capture
    echo    [4] EXIT    - Cancel
    echo.
    set /p CHOICE="  Enter choice (1/2/3/4): "

    if "!CHOICE!"=="4" goto :end
    if "!CHOICE!"=="3" goto :config_train_only
    if "!CHOICE!"=="2" goto :config_fresh
    if "!CHOICE!"=="1" goto :config_add
    goto :config_fresh
) else (
    echo  No trained model found. Starting fresh training.
    goto :config_fresh
)

:config_fresh
set MODE=fresh
goto :configure

:config_add
set MODE=add
goto :configure

:config_train_only
set MODE=train-only
goto :configure

:configure
echo.
echo  -- TRAINING CONFIGURATION --
echo  Current settings:
echo    Samples to capture : %SAMPLES%
echo    Training epochs    : %EPOCHS%
echo    Batch size         : %BATCH_SIZE%
echo    Learning rate      : %LEARNING_RATE%
echo    Pause every        : %PAUSE_EVERY% epochs
echo.
set /p CUSTOM="  Customize settings? (y/n): "
if /i "%CUSTOM%"=="y" (
    echo.
    set /p SAMPLES="  Number of samples to capture [%SAMPLES%]: "
    set /p EPOCHS="  Number of training epochs [%EPOCHS%]: "
    set /p BATCH_SIZE="  Batch size [%BATCH_SIZE%]: "
    set /p LEARNING_RATE="  Learning rate [%LEARNING_RATE%]: "
    set /p PAUSE_EVERY="  Pause every N epochs [%PAUSE_EVERY%]: "
)

echo.
echo  -- FINAL CONFIG --
echo    Mode             : %MODE%
echo    Samples          : %SAMPLES%
echo    Epochs           : %EPOCHS%
echo    Batch Size       : %BATCH_SIZE%
echo    Learning Rate    : %LEARNING_RATE%
echo    Review every     : %PAUSE_EVERY% epochs
echo    GPU              : NVIDIA CUDA (auto-detect)
echo.

echo.
echo  ============================================================
echo  Select Camera Source for Capture:
echo    [1] Built-in Webcam
echo    [2] External Camera (Phone/Tablet via Remote App)
echo.
set /p CAM_CHOICE="  Enter choice (1/2) [Default: 1]: "

if "%CAM_CHOICE%"=="2" (
    set CAMERA_SOURCE=external
    echo.
    echo  [!] WARNING: Ensure the main PARALLAX backend is STOPPED 
    echo      before proceeding. Port 8000 must be free for the 
    echo      training script to receive the external camera feed.
    echo.
    pause
) else (
    set CAMERA_SOURCE=built_in
)

echo.
set /p CONFIRM="  Type 'train' to begin: "
if /i not "%CONFIRM%"=="train" (
    echo  Cancelled.
    goto :end
)

echo.
echo  Starting training pipeline using source: %CAMERA_SOURCE% ...
echo.

python train_classifier.py --samples %SAMPLES% --epochs %EPOCHS% --batch-size %BATCH_SIZE% --lr %LEARNING_RATE% --pause-every %PAUSE_EVERY% --mode %MODE% --source %CAMERA_SOURCE%

echo.
echo  ============================================================
if exist "classifier_weights.pth" (
    echo  [OK] Training complete! Model saved to classifier_weights.pth
    echo  [OK] The main PARALLAX system will auto-load these weights.
) else (
    echo  [!!] No model weights found. Training may have failed.
)
echo  ============================================================

:end
echo.
pause
