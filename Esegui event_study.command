#!/bin/bash
cd "$(dirname "$0")"
.venv/bin/python event_study.py
echo
read -p "Premi INVIO per chiudere questa finestra..."
