@echo off
echo ============================================================
echo Starting AI ID Document Extractor (React + FastAPI Stack)
echo ============================================================

echo 1. Starting Python FastAPI Backend on port 8000...
start "Python FastAPI Backend (Port 8000)" cmd /k "cd /d python_service && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo 2. Starting React Frontend on port 5173...
start "React Client (Port 5173)" cmd /k "cd /d client && npm run dev"

echo ============================================================
echo All services launched!
echo - React Frontend: http://localhost:5173
echo - Python FastAPI API: http://localhost:8000/docs
echo ============================================================
pause
