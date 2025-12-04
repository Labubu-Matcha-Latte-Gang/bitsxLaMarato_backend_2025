# Usa una imagen base un poco más completa para el build (evita compilar desde cero)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Instalar dependencias de sistema (ffmpeg, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 2. Copiar SOLO requirements.txt primero
COPY requirements.txt .

RUN pip install --no-cache-dir torch --index-url https://download.pytorc h.org/whl/cpu

# 3. Instalar librerías usando CACHÉ DE DOCKER
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch --index-url https://download.pytorch.org/whl/cpu

# 4. Descargar modelos de IA (Capa pesada pero estática)
RUN python -m spacy download ca_core_news_md && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# 5. FINALMENTE copiamos tu código
COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]