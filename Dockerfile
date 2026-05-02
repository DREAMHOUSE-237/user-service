FROM python:3.11-slim

# ---------------------------
# Environment variables
# ---------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_ENV=production
ENV MYSQL_DATABASE=userservice_db
ENV MYSQL_USER=root
ENV MYSQL_PASSWORD=root
ENV MYSQL_HOST=host.docker.internal
ENV MYSQL_PORT=3306

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
    && pip install mysqlclient

# ---------------------------
# Copy project files
# ---------------------------
COPY . /app/

# ---------------------------
# Expose port
# ---------------------------
EXPOSE 8000

# ---------------------------
# Run Django server
# ---------------------------
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
