import logging
from scapy.sendrecv import sniff, sendp
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, UDP
from scapy.layers.dhcp import BOOTP, DHCP
from logutil import safe_run
from netutil import parse_arch, is_ipxe_client, iface_mac

PXE_OPT43 = b"\x06\x01\x08"  # disable PXE multicast

def _warn_dhcp_conflict(pkt, my_ip: str):
    if IP in pkt:
        src = pkt[IP].src
        if src not in ("0.0.0.0", my_ip, "255.255.255.255"):
            logging.warning("⚠ Detected other DHCP responder: %s (possible conflict)", src)

def _build_reply(cfg, pkt, msgtype_code: int, dport: int, bootfile: bytes):
    opts = [
        ("message-type", msgtype_code),
        ("server_id", cfg.server_ip.encode()),
        ("vendor_class_id", b"PXEClient"),
        (43, PXE_OPT43),
        (66, cfg.server_ip.encode()),
        (67, bootfile),
        "end",
    ]
    return (
        Ether(src=iface_mac(cfg.iface), dst="ff:ff:ff:ff:ff:ff")
        / IP(src=cfg.server_ip, dst="255.255.255.255", ttl=64)
        / UDP(sport=67, dport=dport)
        / BOOTP(
            op=2,
            chaddr=pkt[BOOTP].chaddr,
            xid=pkt[BOOTP].xid,
            yiaddr="0.0.0.0",
            siaddr=cfg.server_ip,
            file=bootfile,
            flags=0x8000,
        )
        / DHCP(options=opts)
    )

@safe_run
def dhcp_proxy(cfg, stop_event):
    logging.info("DHCP Proxy listening (udp 67/68) on iface=%r ...", cfg.iface)

    def handle(pkt):
        if stop_event.is_set():
            return
        if not (pkt.haslayer(DHCP) and pkt.haslayer(BOOTP)):
            return

        _warn_dhcp_conflict(pkt, cfg.server_ip)

        opt = dict((o if isinstance(o, tuple) else ("end", None)) for o in pkt[DHCP].options)
        mt = opt.get("message-type", None)  # 1=Discover, 3=Request
        arch = parse_arch(opt)

        if is_ipxe_client(opt):
            boot, phase = cfg.bootfile_ipxe, "iPXE"
        else:
            if arch in (6, 7, 9):
                boot, phase = cfg.bootfile_uefi, "UEFI PXE"
            else:
                boot, phase = cfg.bootfile_bios, "BIOS PXE"

        if mt == 1:
            sendp(_build_reply(cfg, pkt, 2, 4011, boot), iface=cfg.iface, verbose=0)
            sendp(_build_reply(cfg, pkt, 2,   68, boot), iface=cfg.iface, verbose=0)
            logging.info("[PXE] Discover -> Offer (phase=%s, arch=%s, boot=%s)", phase, arch, boot.decode(errors="ignore"))
        elif mt == 3:
            sendp(_build_reply(cfg, pkt, 5, 4011, boot), iface=cfg.iface, verbose=0)
            sendp(_build_reply(cfg, pkt, 5,   68, boot), iface=cfg.iface, verbose=0)
            logging.info("[PXE] Request  -> Ack   (phase=%s, arch=%s, boot=%s)", phase, arch, boot.decode(errors="ignore"))

    bpf = "(udp dst port 67 or udp dst port 68 or udp src port 67 or udp src port 68)"
    while not stop_event.is_set():
        sniff(filter=bpf, prn=handle, store=0, iface=cfg.iface, timeout=1)
    logging.info("DHCP Proxy stopped.")
