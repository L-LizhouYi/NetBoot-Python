#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PXE / iPXE modular server
- DHCP Proxy: BIOS->undionly.kpxe, UEFI->ipxe.efi, iPXE->boot.ipxe
- TFTP: OACK echo + stop-and-wait retrans
- HTTP: static files from srv/http (ThreadingHTTPServer)
- Auto-pick iface by --ip
"""

import argparse
import logging
import os
import signal
import sys
import threading

from config import Config
from logutil import setup_logging
from netutil import pick_iface_by_ip, iface_mac
from tftp_server import tftp_server
from http_server import http_server
from dhcp_proxy import dhcp_proxy

def main():
    ap = argparse.ArgumentParser(description="PXE/iPXE Server (BIOS + UEFI)")
    ap.add_argument("--ip", dest="server_ip", required=True, help="Server IP (also DHCP next-server)")
    ap.add_argument("--tftp", dest="tftp_port", type=int, default=69, help="TFTP port")
    ap.add_argument("--http", dest="http_port", type=int, default=8080, help="HTTP port")
    ap.add_argument("--bind", dest="bind", default="0.0.0.0", help="Bind address for TFTP/HTTP")
    ap.add_argument("--log-level", dest="log_level", default="INFO")
    args = ap.parse_args()

    cfg = Config(server_ip=args.server_ip, tftp_port=args.tftp_port,
                 http_port=args.http_port, bind=args.bind, log_level=args.log_level)

    setup_logging(cfg.log_level)

    # Windows-specific pcap backend for Scapy
    try:
        if os.name == "nt":
            from scapy.config import conf  # lazy import
            conf.use_pcap = True
    except Exception:
        pass

    try:
        cfg.iface = pick_iface_by_ip(cfg.server_ip)
    except Exception as e:
        logging.error("Failed to select interface: %s", e)
        sys.exit(2)

    os.makedirs(cfg.tftp_root, exist_ok=True)
    os.makedirs(cfg.http_root, exist_ok=True)

    logging.info("TFTP root: %s", cfg.tftp_root)
    logging.info("HTTP root: %s", cfg.http_root)
    from scapy.arch import get_if_addr
    logging.info("Using iface: %s  IP: %s  MAC: %s", cfg.iface, get_if_addr(cfg.iface), iface_mac(cfg.iface))
    logging.info("Server IP (next-server): %s", cfg.server_ip)
    logging.info("Starting services: TFTP + HTTP + DHCP Proxy")

    stop_event = threading.Event()

    def _stop(sig, _):
        logging.info("Signal %s received, shutting down...", sig)
        stop_event.set()

    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(s, _stop)
        except Exception:
            pass

    t1 = threading.Thread(target=tftp_server, args=(cfg, stop_event), daemon=True)
    t2 = threading.Thread(target=http_server, args=(cfg, stop_event), daemon=True)
    t1.start(); t2.start()
    try:
        dhcp_proxy(cfg, stop_event)
    finally:
        stop_event.set()
        t1.join(timeout=2)
        t2.join(timeout=2)
        logging.info("All services stopped.")

if __name__ == "__main__":
    main()
