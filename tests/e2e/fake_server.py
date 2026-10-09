"""Servidor HTTP falso para o teste ponta a ponta.

GET /cpu?ms=N gasta N ms de CPU por requisição. Vários processos de trabalho
compartilham a porta (SO_REUSEPORT), então a capacidade escala com os núcleos
disponíveis (use `taskset` para limitar).
"""
import argparse
import multiprocessing as mp
import signal
import socket
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        ms = float(parse_qs(urlparse(self.path).query).get("ms", ["10"])[0])
        fim = time.process_time() + ms / 1000
        while time.process_time() < fim:
            pass
        corpo = b"ok\n"
        self.send_response(200)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *args):
        pass


class Servidor(HTTPServer):
    request_queue_size = 1024

    def server_bind(self):
        # SO_REUSEPORT manual (allow_reuse_port só existe no Python ≥ 3.11)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        super().server_bind()

    def handle_error(self, request, client_address):
        pass  # cliente desistiu (timeout do vegeta na saturação): não poluir a saída


def trabalhar(porta):
    Servidor(("127.0.0.1", porta), Handler).serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--porta", type=int, default=18080)
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    # SIGTERM vira saída normal, para o multiprocessing encerrar os processos filhos (daemon).
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    processos = [mp.Process(target=trabalhar, args=(args.porta,), daemon=True) for _ in range(args.workers)]
    for p in processos:
        p.start()
    for p in processos:
        p.join()
