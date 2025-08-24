FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=5050

RUN apt-get update && apt-get install -y --no-install-recommends \
    libopenslide0 openslide-tools \
    libglib2.0-0 libjpeg62-turbo libopenjp2-7 libpng16-16 zlib1g \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Jika proyek Anda installable (PEP 621) gunakan ini:
COPY pyproject.toml ./
RUN pip install --upgrade pip build setuptools wheel \
 && pip install gunicorn \
 && python -m build --wheel \
 || echo "Lewati build wheel, akan pakai editable later"

# Salin source lalu install editable (fallback yang umum)
COPY app ./app
COPY wsgi.py ./
COPY public ./public
COPY slides ./slides
COPY README.md ./

# Coba install dari pyproject; jika gagal, install requirements di dalam app (opsional)
RUN pip install -e . || true

# Expose
EXPOSE 5050
CMD ["gunicorn", "-w", "4", "-k", "gthread", "-b", "0.0.0.0:5050", "app.wsgi:app", "--timeout", "120"]

