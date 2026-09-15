#!/bin/bash
cd "$(dirname "$0")"

if ! curl -s -o /dev/null "http://localhost:8765/"; then
  echo "Avvio il server locale..."
  nohup .venv/bin/python server.py > server.log 2>&1 &
  sleep 1
fi

echo "Aggiorno l'Oracolo dell'Oro con dati e notizie di oggi..."
.venv/bin/python oracolo.py

open -a Safari "http://localhost:8765/index.html"
