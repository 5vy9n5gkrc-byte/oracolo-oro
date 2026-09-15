"""
Piccolo server locale per l'Oracolo dell'Oro.

Serve la pagina HTML della cartella ed espone:
  - /aggiorna (POST): rilancia oracolo.py con dati e notizie freschi,
    chiamato dal pulsante "Aggiorna dati".
  - /prezzo-live (GET): scarica al volo il grafico intraday dell'oro da
    Yahoo Finance e lo ridà in JSON. Il browser non puo' chiamare Yahoo
    direttamente (blocco CORS), ma il nostro server si', quindi fa da
    ponte per il grafico "quasi in diretta" della pagina.
"""

import http.server
import socketserver
import subprocess
import sys
import os
import json
import urllib.request

PORTA = 8765
CARTELLA = os.path.dirname(os.path.abspath(__file__))
YF_INTRADAY = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?range=1d&interval=1m"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=CARTELLA, **kwargs)

    def do_GET(self):
        if self.path.startswith("/prezzo-live"):
            self._prezzo_live()
            return
        super().do_GET()

    def _prezzo_live(self):
        try:
            req = urllib.request.Request(YF_INTRADAY, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                dati = json.load(resp)

            risultato = dati["chart"]["result"][0]
            timestamp = risultato["timestamp"]
            chiusure = risultato["indicators"]["quote"][0]["close"]
            punti = [
                {"t": t * 1000, "prezzo": p}
                for t, p in zip(timestamp, chiusure) if p is not None
            ]
            corpo = json.dumps({"punti": punti}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(corpo)
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(str(e).encode("utf-8"))

    def do_POST(self):
        if self.path != "/aggiorna":
            self.send_response(404)
            self.end_headers()
            return

        risultato = subprocess.run(
            [sys.executable, os.path.join(CARTELLA, "oracolo.py")],
            cwd=CARTELLA, capture_output=True, text=True,
        )
        if risultato.returncode == 0:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(risultato.stderr.encode("utf-8"))

    def log_message(self, format, *args):
        pass  # niente log rumorosi nel terminale


class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
    # senza il ThreadingMixIn, mentre gira /aggiorna (10-20 secondi) il
    # grafico live in /prezzo-live resterebbe bloccato in attesa
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with Server(("127.0.0.1", PORTA), Handler) as httpd:
        print(f"Server in ascolto su http://localhost:{PORTA}")
        httpd.serve_forever()
