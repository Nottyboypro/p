FROM python:3.11-slim



# Install system dependencies needed by Pillow / qrcode
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

RUN pip3 install --no-cache-dir -U -r requirements.txt



CMD gunicorn main:app
