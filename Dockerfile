FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY . .

# Installa uv per velocizzare il setup delle dipendenze e installa i pacchetti
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv \
    && uv pip install --system --no-cache -r requirements.txt \
    && chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "stremio_catalog_provider.api:app", "--host", "0.0.0.0", "--port", "8000"]
