Write-Host "Starting FastAPI Development Server..." -ForegroundColor Green
python -m fastapi_cli dev main.py 

cd ..
cd ..
. .\venv\Scripts\activate
 cd .\ARGBackend\backend-db\
uvicorn main:app --reload


Find the process:
lsof -i :8000 or sudo netstat -tulnp | grep 8000
lsof -i or sudo netstat -tulnp

Kill process
kill -9 <PID>