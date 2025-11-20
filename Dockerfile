FROM python:3.11-slim

# Environment
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System dependencies for Pillow / qrcode
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
 && rm -rf /var/lib/apt/lists/*

# App directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt /app/
RUN pip3 install --upgrade pip \
 && pip3 install -U -r requirements.txt

# Copy project files
COPY . /app

# Port expose
EXPOSE 5000

# ⭐ Your required CMD ⭐
CMD ["gunicorn", "main:app"]
