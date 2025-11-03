import os
import logging
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from logutil import safe_run

class _StaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logging.info("HTTP: " + fmt % args)

@safe_run
def http_server(cfg, stop_event):
    os.makedirs(cfg.http_root, exist_ok=True)
    cwd = os.getcwd()
    os.chdir(cfg.http_root)
    try:
        httpd = ThreadingHTTPServer((cfg.bind, cfg.http_port), _StaticHandler)
        logging.info("HTTP Server on %s:%s, root=%s", cfg.bind, cfg.http_port, cfg.http_root)
        while not stop_event.is_set():
            httpd.handle_request()
        httpd.server_close()
    finally:
        os.chdir(cwd)
    logging.info("HTTP Server stopped.")
