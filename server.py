"""
Piccolo server locale per l'Oracolo dell'Oro.

Serve la pagina HTML della cartella ed espone /aggiorna: quando il
pulsante "Aggiorna dati" nella pagina lo chiama, rilancia oracolo.py
con dati e notizie freschi, poi la pagina si ricarica da sola.
"""

import http.server
import socketserver
import subprocess
import sys
import os

PORTA = 8765
CARTELLA = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=CARTELLA, **kwargs)

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


class Server(socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    with Server(("127.0.0.1", PORTA), Handler) as httpd:
        print(f"Server in ascolto su http://localhost:{PORTA}")
        httpd.serve_forever()
