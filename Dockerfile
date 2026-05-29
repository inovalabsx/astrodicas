FROM python:3.12-slim

WORKDIR /app

# Dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY src/ /app/src/

EXPOSE 8000

# Suporta override via APP_MODULE (ex: vendas_bot.main:app)
CMD ["sh", "-c", "uvicorn ${APP_MODULE:-src.main:app} --host 0.0.0.0 --port ${PORT:-8000}"]
