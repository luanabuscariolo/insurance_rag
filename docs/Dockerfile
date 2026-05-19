# ── Stage 1: builder ──────────────────────────────────────────────────────────
# Instala dependências num estágio separado para manter a imagem final menor
FROM python:3.11-slim AS builder

WORKDIR /app

# instala dependências do sistema necessárias para compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ── Stage 2: runner ───────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# copia apenas o que foi instalado, sem ferramentas de build
COPY --from=builder /root/.local /root/.local

# copia o código da aplicação
COPY app/ ./app/
COPY data/policies/ ./data/policies/

# cria pastas necessárias em runtime
RUN mkdir -p ./data/chroma

# PATH para encontrar os executáveis instalados pelo pip
ENV PATH=/root/.local/bin:$PATH

# usuário não-root para segurança
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# porta que o FastAPI vai escutar
EXPOSE 8000

# health check que o Docker vai usar
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# comando de inicialização
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
