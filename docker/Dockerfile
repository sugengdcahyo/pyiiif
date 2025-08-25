FROM python:3.12-slim

# Update system packages to latest versions to reduce vulnerabilities
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=5050

# Install OpenSlide dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenslide0 openslide-tools \
    libglib2.0-0 libjpeg62-turbo libopenjp2-7 libpng16-16 libtiff-dev zlib1g \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Jika proyek Anda installable (PEP 621) gunakan ini:
COPY pyproject.toml ./
RUN pip install --upgrade pip setuptools wheel \
 && pip install gunicorn \
 && pip install .

# Salin source lalu install editable (fallback yang umum)
COPY . .

# Coba install dari pyproject; jika gagal, install requirements di dalam app (opsional)
# RUN pip install -e . || true

# Expose
EXPOSE 5050
CMD ["gunicorn", "-w", "2", "-k", "gthread", "--thread", "2", "-b", "0.0.0.0:5050", "wsgi:app", "--timeout", "120"]

