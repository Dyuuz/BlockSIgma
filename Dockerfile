# ---- Base (CPU) ----
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    TF_CPP_MIN_LOG_LEVEL=2

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

COPY app/static ./app/static
COPY app/templates ./app/templates

COPY . .

COPY start.sh ./
RUN chmod +x ./start.sh

CMD sh ./start.sh
