FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    python3-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt \
    && pip install mysqlclient gunicorn

COPY . /app/

EXPOSE 8000

# ──────────────────────────────────────────────────────────────────────
# CORRECTIONS APPLIQUÉES :
#
# 1. --preload
#    Charge Django dans le master Gunicorn AVANT de forker les workers.
#    → apps.py ready() est appelé UNE SEULE FOIS, dans le master.
#    → Les workers forkés héritent de l'état Django sans rappeler ready().
#    → Élimine le _DeadlockError sur user_service.urls causé par des
#      imports concurrent au démarrage des threads dans ready().
#
# 2. GUNICORN_MAIN_PID=$$
#    $$ = PID du shell = PID du master Gunicorn.
#    apps.py compare os.getpid() avec cette valeur pour savoir s'il
#    est dans le master (→ lance les threads) ou un worker (→ skip).
#
# 3. --workers 1 --threads 4
#    1 seul worker gthread est suffisant pour un service Django léger
#    avec Eureka + consumers en threads. Augmenter les workers sans
#    --preload multipliait les threads Eureka/consumers par worker.
# ──────────────────────────────────────────────────────────────────────
CMD ["sh", "-c", "GUNICORN_MAIN_PID=$$ exec gunicorn user_service.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 1 \
    --threads 4 \
    --worker-class gthread \
    --preload \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 30"]
    