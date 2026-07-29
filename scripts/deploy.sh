#!/bin/bash
set -e

# Trova la directory del progetto (rispetto alla posizione dello script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Carica il file .env se esiste
if [ -f "$PROJECT_DIR/.env" ]; then
    echo "Caricamento variabili d'ambiente da $PROJECT_DIR/.env..."
    # Carica le righe che non sono commenti ed esportale
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

# Verifica che le variabili necessarie siano impostate
if [ -z "$DEPLOY_HOST" ]; then
    echo "Errore: DEPLOY_HOST non è impostata. Configurala in .env o come variabile d'ambiente."
    exit 1
fi

if [ -z "$DEPLOY_PATH" ]; then
    echo "Errore: DEPLOY_PATH non è impostata. Configurala in .env o come variabile d'ambiente."
    exit 1
fi

echo "Avvio del deploy su ${DEPLOY_HOST} in ${DEPLOY_PATH}..."

# Esegui i comandi via SSH
ssh "$DEPLOY_HOST" << EOF
  set -e
  echo "Connesso all'host: \$(hostname)"
  
  # Accedi alla cartella remota del progetto
  cd "$DEPLOY_PATH"
  echo "Directory corrente sul server: \$(pwd)"
  
  # Scarica le ultime novità dal repository git
  echo "Pull dei cambiamenti da git..."
  git pull
  
  # Avvio/Ricostruzione container con docker compose
  if [ -f "docker-compose.override.yml" ]; then
      echo "Trovato docker-compose.override.yml. Avvio con override..."
      docker compose up -d --build
  else
      echo "Avvio standard (senza override)..."
      docker compose up -d --build
  fi
  
  echo "Deploy completato con successo sul server remoto!"
EOF
