import logging
import re
from scapy.config import conf
from scapy.arch import get_if_list, get_if_addr, get_if_hwaddr

def pick_iface_by_ip(server_ip: str) -> str:
    """Pick an interface that has the given IP, or best route fallback."""
    for iface in get_if_list():
        try:
            if get_if_addr(iface) == server_ip:
                return iface
        except Exception:
            pass
    try:
        route = conf.route.route(server_ip)
        if isinstance(route, tuple) and len(route) >= 3 and isinstance(route[2], str):
            return route[2]
    except Exception:
        pass
    lst = get_if_list()
    if lst:
        logging.warning("No exact iface for %s, fallback to %s", server_ip, lst[0])
        return lst[0]
    raise RuntimeError("No usable network interface detected")

def iface_mac(iface: str) -> str:
    try:
        mac = get_if_hwaddr(iface)
        if mac and mac != "00:00:00:00:00:00":
            return mac
    except Exception:
        pass
    return "02:00:5e:00:53:01"

def parse_arch(opt) -> int:
    """Parse client architecture (DHCP option 93). Returns 0 (BIOS) if unknown."""
    raw = opt.get(93) or opt.get("client_architecture")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, (bytes, bytearray)) and len(raw) >= 2:
        return int.from_bytes(raw[:2], "big")
    vci = opt.get("vendor_class_id", b"")
    if isinstance(vci, (bytes, bytearray)):
        vci = vci.decode(errors="ignore")
    m = re.search(r"Arch:0*([0-9]+)", vci or "")
    return int(m.group(1)) if m else 0

def is_ipxe_client(opt) -> bool:
    """Detect iPXE via vendor/user class or option 175 presence."""
    vci = opt.get("vendor_class_id", b"")
    if isinstance(vci, (bytes, bytearray)):
        try:
            vci = vci.decode(errors="ignore")
        except Exception:
            vci = ""
    if isinstance(vci, str) and "ipxe" in vci.lower():
        return True
    ucls = opt.get("user_class")
    if ucls is not None:
        if isinstance(ucls, (bytes, bytearray)):
            try:
                if "ipxe" in ucls.decode(errors="ignore").lower():
                    return True
            except Exception:
                pass
        elif isinstance(ucls, str) and "ipxe" in ucls.lower():
            return True
        elif isinstance(ucls, (list, tuple)):
            for it in ucls:
                if isinstance(it, (bytes, bytearray)):
                    try:
                        if "ipxe" in it.decode(errors="ignore").lower():
                            return True
                    except Exception:
                        continue
                elif isinstance(it, str) and "ipxe" in it.lower():
                    return True
    return 175 in opt
