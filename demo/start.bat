@echo off
color 0b
echo =========================================
echo       PARALLAX SYSTEM STARTUP SCRIPT     
echo =========================================
echo.

echo [1/3] Checking Python dependencies...
python -c "import torch, cv2, fastapi, uvicorn" 2>nul || (
    echo Required modules missing. Installing dependencies...
    pip install -r requirements.txt
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
)

echo.
echo [2/3] Starting Python FastAPI Backend in background...
start /B python backend.py

:: Wait a moment to ensure backend starts before the frontend hits it
timeout /t 3 /nobreak >nul

echo.
echo [3/3] Starting React Frontend Dashboard...
echo =========================================
echo - API Server: http://localhost:8000
echo - Dashboard:  http://localhost:5173
echo =========================================
echo.
echo Keep this window open! Press Ctrl+C to stop everything.
echo.

cd frontend
npm run dev
