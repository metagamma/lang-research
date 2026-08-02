#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor del visor. Stdlib y nada mas.

POR QUE SSE Y NO WEBSOCKET
--------------------------
El flujo es unidireccional: el servidor manda, el cliente mira. El control
(pausa, velocidad, parametros) cabe en un POST corriente. Server-Sent
Events hace exactamente eso, funciona sobre `http.server` de la biblioteca
estandar, y el navegador trae reconexion automatica de serie.

WebSocket exigiria una dependencia para ganar un canal de vuelta que no
necesitamos. Este proyecto ha corrido toda su vida con numpy y nada mas;
no vale la pena romper eso por comodidad.

RUTAS
-----
    GET  /world     el mundo (sentidos, lugares con coordenadas, tipos)
    GET  /state     instantanea actual — permite recargar sin historia
    GET  /stream    SSE: episodio | generacion | instantanea | corte | fin
    POST /control   {"pausa":bool, "episodios_por_seg":int, "parametros":{}}
    GET  /          el cliente compilado, si existe
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENTE = os.path.join(RAIZ, "client", "dist")


def _handler(vivo, bus, mundo_json):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass          # sin ruido en consola: la simulacion ya escribe

        # -- utilidades -------------------------------------------------
        def _json(self, obj, code=200):
            cuerpo = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(cuerpo)

        # -- GET --------------------------------------------------------
        def do_GET(self):
            ruta = self.path.split("?")[0]
            if ruta == "/world":
                return self._json(mundo_json)
            if ruta == "/state":
                return self._json(vivo.instantanea_actual())
            if ruta == "/stream":
                return self._stream()
            return self._estatico(ruta)

        def _stream(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            cid = bus.suscribir()
            try:
                # lo primero, el estado: quien llega tarde no necesita historia
                self._evento("instantanea", vivo.instantanea_actual())
                vacios = 0
                while True:
                    lote = bus.recoger(cid)
                    if not lote:
                        vacios += 1
                        if vacios > 40:      # ~4 s
                            self.wfile.write(b": latido\n\n")
                            self.wfile.flush()
                            vacios = 0
                        threading.Event().wait(0.1)
                        continue
                    vacios = 0
                    for canal, dato in lote:
                        self._evento(canal, dato)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass                          # el navegador se fue; normal
            finally:
                bus.cancelar(cid)

        def _evento(self, canal, dato):
            cuerpo = json.dumps(dato, ensure_ascii=False, separators=(",", ":"))
            self.wfile.write(f"event: {canal}\ndata: {cuerpo}\n\n"
                             .encode("utf-8"))
            self.wfile.flush()

        def _estatico(self, ruta):
            if not os.path.isdir(CLIENTE):
                return self._json({"aviso": "cliente sin compilar",
                                   "rutas": ["/world", "/state", "/stream",
                                             "/control"]}, 404)
            rel = "index.html" if ruta in ("/", "") else ruta.lstrip("/")
            f = os.path.normpath(os.path.join(CLIENTE, rel))
            if not f.startswith(CLIENTE) or not os.path.isfile(f):
                f = os.path.join(CLIENTE, "index.html")
            tipo = ("text/html" if f.endswith(".html") else
                    "text/javascript" if f.endswith(".js") else
                    "text/css" if f.endswith(".css") else
                    "application/octet-stream")
            with open(f, "rb") as fh:
                cuerpo = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", f"{tipo}; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        # -- POST -------------------------------------------------------
        def do_POST(self):
            if self.path.split("?")[0] != "/control":
                return self._json({"error": "ruta desconocida"}, 404)
            n = int(self.headers.get("Content-Length") or 0)
            try:
                orden = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._json({"error": "json invalido"}, 400)
            return self._json(vivo.aplicar(orden))

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

    return H


def servir(cfg, n_tribes, seed, port=8080, episodios_por_seg=30,
           snap_cada=10):
    """Arranca simulacion y servidor. No vuelve hasta Ctrl-C."""
    from .stream import Bus, Vivo
    from .world import WORLDS_DIR

    bus = Bus()
    vivo = Vivo(cfg, n_tribes, seed, bus, episodios_por_seg, snap_cada)

    ruta = cfg.world if os.path.isfile(cfg.world) else os.path.join(
        WORLDS_DIR, f"{cfg.world}.json")
    with open(ruta, encoding="utf-8") as fh:
        mundo = json.load(fh)

    # La simulacion en su hilo, y en daemon: Ctrl-C no se queda colgado.
    hilo = threading.Thread(target=vivo.correr, daemon=True, name="simulacion")
    hilo.start()

    srv = ThreadingHTTPServer(("0.0.0.0", port), _handler(vivo, bus, mundo))
    srv.daemon_threads = True
    print(f"  mundo '{mundo.get('name')}' — {len(mundo['kinds'])} tipos, "
          f"{n_tribes} tribus, banda {cfg.max_pop}")
    print(f"  http://localhost:{port}/stream   (SSE)")
    print(f"  http://localhost:{port}/state    (instantanea)")
    print("  Ctrl-C para parar\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print(f"\n  parado en la generacion {vivo.gen}")
    finally:
        vivo.parar = True
        srv.server_close()
