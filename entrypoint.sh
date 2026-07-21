#!/bin/bash
set -e

# Se stiamo avviando il web server, eseguiamo le migrazioni
if [[ "$1" == "uvicorn" || "$*" == *"stremio_catalog_provider.api"* ]]; then
  echo "Esecuzione delle migrazioni Alembic..."
  alembic upgrade head
fi

exec "$@"
