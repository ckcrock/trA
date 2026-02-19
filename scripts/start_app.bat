@echo off
echo Starting Hybrid Trading System...

echo 1. Starting Database and Monitoring Stack (Docker)...
docker-compose up -d

echo 2. Installing Python Dependencies...
pip install -r requirements.txt

echo 3. Starting Trading Node API...
echo Access the UI at: src/ui/index.html (Open in Browser)
echo Access API Docs at: http://localhost:8000/api/docs
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

pause
