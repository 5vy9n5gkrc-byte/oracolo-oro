#!/bin/bash
cd "$(dirname "$0")"
echo "Effetto vero da iniettare nei dati sintetici."
echo "Lascia vuoto per 0 (nessun segnale), oppure digita un numero es. 0.008"
read -p "Effetto: " effect
effect=${effect:-0.0}
.venv/bin/python gold_predictor.py --effect "$effect"
echo
read -p "Premi INVIO per chiudere questa finestra..."
