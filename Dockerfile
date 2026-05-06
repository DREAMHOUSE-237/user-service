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
# CORRECTIONS :
#
# 1. --workers 1 --threads 2 --worker-class gthread
#    Avant, Gunicorn utilisait probablement le défaut (1 worker sync) mais
#    dans certaines configs --workers 2+ multipliait les subprocesses.
#    1 worker gthread suffit pour un service Django léger.
#
# 2. --preload
#    Charge Django dans le master AVANT de forker les workers.
#    → apps.py ready() est appelé UNE SEULE FOIS dans le master.
#    → Les workers forkés héritent du state Django sans rappeler ready().
#
# 3. GUNICORN_MAIN_PID=$$
#    $$ = PID du shell qui lance la commande = PID du master Gunicorn.
#    apps.py compare os.getpid() avec cette valeur pour savoir s'il
#    est dans le master (→ lance threads) ou dans un worker (→ skip).
#    C'est la façon la plus fiable de distinguer master/workers avec --preload.
# ──────────────────────────────────────────────────────────────────────
CMD ["sh", "-c", "GUNICORN_MAIN_PID=$$ exec gunicorn user_service.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 1 \
    --threads 2 \
    --worker-class gthread \
    --preload \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 30"]