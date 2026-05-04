FROM python:3.11-slim

# ---------------------------
# Environment variables
# ---------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---------------------------
# Working directory
# ---------------------------
WORKDIR /app

# ---------------------------
# System dependencies for Linux + MySQL
# ---------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    python3-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------
# Install Python dependencies
# ---------------------------
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt \
    && pip install mysqlclient gunicorn

# ---------------------------
# Copy project files
# ---------------------------
COPY . /app/

# ---------------------------
# Expose port
# ---------------------------
EXPOSE 8000

# ---------------------------
# Run with gunicorn
# ---------------------------
CMD ["gunicorn", "user_service.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]