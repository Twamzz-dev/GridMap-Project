FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Install base system utilities and build dependencies
RUN apt-get update && apt-get install -y gcc build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY . .

# For local dev, accept .env
ENV PYTHONUNBUFFERED=1

# Uvicorn as entrypoint
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
