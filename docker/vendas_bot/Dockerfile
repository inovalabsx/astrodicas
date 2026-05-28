FROM python:3.12-slim

WORKDIR /app

# Dependências do sistema (incluindo fontes para PDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Python deps (compartilha o mesmo requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY src/ /app/src/

EXPOSE 3000

# Ponto de entrada: bot de vendas
CMD ["uvicorn", "src.vendas_bot.main:app", "--host", "0.0.0.0", "--port", "3000"]
