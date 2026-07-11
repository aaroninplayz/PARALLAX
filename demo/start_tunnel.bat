@echo off
color 0b
echo =========================================
echo       PARALLAX CLOUDFLARE TUNNEL SCRIPT   
echo =========================================
echo.

if not exist cloudflared.exe (
    echo [1/2] Downloading Cloudflared (Quick Tunnels)...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile 'cloudflared.exe'"
) else (
    echo [1/2] Cloudflared is ready.
)

echo.
echo [2/2] Starting Quick Tunnel for Frontend (Port 5173)...
echo.
echo ==========================================================
echo IMPORTANT: When the tunnel URL appears (ends in trycloudflare.com),
echo you can use it to access the frontend from anywhere.
echo.
echo Note: For the React Dashboard to fully communicate with the 
echo backend over the internet, both frontend and backend need
echo to be exposed or hosted together. This tunnel gives you
echo quick access to the UI.
echo ==========================================================
echo.
cloudflared.exe tunnel --url http://localhost:5173/
pause
