#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TFTP server (robust, BIOS + UEFI/iPXE compatible)

期望由 main.py 调用：
    from tftp_server import tftp_server
    t = threading.Thread(target=tftp_server, args=(cfg, stop_event), daemon=True)
    t.start()

cfg 需要包含属性：
    - bind: str             监听地址（通常 0.0.0.0）
    - tftp_port: int        TFTP 端口（通常 69）
    - tftp_root: str        文件根目录

stop_event: threading.Event 用于优雅退出。

要点：
- 停等式传输、超时重传、blksize 协商
- BIOS 首 RRQ（仅 tsize）→ 只回 OACK(tsize)，不发数据
- UEFI ipxe.efi 首 RRQ（tsize+blksize）→ 只回 OACK(tsize)，不发数据
- 其它情况：按请求回 OACK（tsize/blksize），必要时等待 ACK(0) 再开始 DATA(1)
- Windows：禁用 UDP “connreset” 异常
"""

import os
import socket
import logging

# ----------------- 常量 -----------------
_TFTP_OP_RRQ  = 1
_TFTP_OP_DATA = 3
_TFTP_OP_ACK  = 4
_TFTP_OP_OACK = 6
_TFTP_OP_ERR  = 5

_ERR_NOT_FOUND = b"\x00\x05\x00\x01File not found\x00"

# ----------------- 工具 -----------------
def _send_oack(sock: socket.socket, addr, pairs):
    """
    发送 OACK；pairs 为 [(key, value), ...]，会按给定顺序编码
    """
    payload = b""
    for k, v in pairs:
        payload += k.encode() + b"\x00" + str(v).encode() + b"\x00"
    pkt = b"\x00\x06" + payload
    sock.sendto(pkt, addr)

def _maybe_drain_ack0(sock: socket.socket, client_addr, timeout=0.5):
    """
    一些固件会在 OACK 后回 ACK(0)。为了稳妥，尝试快速接收并丢弃 ACK(0)。
    即便没收到也不报错（容忍“直接发 DATA(1)”的模式）。
    """
    try:
        sock.settimeout(timeout)
        pkt, raddr = sock.recvfrom(1500)
        if raddr == client_addr and len(pkt) >= 4 and pkt[1] == _TFTP_OP_ACK and pkt[2:4] == b"\x00\x00":
            logging.debug(f"TFTP[{client_addr}] got ACK(0) after OACK")
            return True
    except socket.timeout:
        pass
    except Exception as e:
        logging.debug(f"TFTP[{client_addr}] drain ACK0 ignore: {e}")
    finally:
        try:
            sock.settimeout(2.0)
        except Exception:
            pass
    return False

def _tftp_stream(sock: socket.socket, client_addr, filepath: str, blksize: int):
    """
    停等式数据发送：按 blksize 逐块发送，等待 ACK，重传 3 次
    """
    try:
        with open(filepath, "rb") as f:
            block = 1
            while True:
                chunk = f.read(blksize)
                data = b"\x00\x03" + block.to_bytes(2, "big") + chunk  # DATA
                for attempt in range(3):
                    sock.sendto(data, client_addr)
                    try:
                        sock.settimeout(2.0)
                        ack, raddr = sock.recvfrom(1500)
                    except socket.timeout:
                        if attempt == 2:
                            logging.warning(f"TFTP[{client_addr}] ACK timeout block={block} blksize={blksize}")
                            return
                        continue
                    if raddr != client_addr or len(ack) < 4 or ack[1] != _TFTP_OP_ACK:
                        continue
                    if int.from_bytes(ack[2:4], "big") != block:
                        continue
                    break  # 收到匹配 ACK
                if len(chunk) < blksize:
                    return  # 最后一块
                block = (block + 1) & 0xFFFF
    except FileNotFoundError:
        sock.sendto(_ERR_NOT_FOUND, client_addr)
        logging.warning(f"TFTP File not found: {filepath}")
    except Exception as e:
        logging.exception(f"TFTP session error: {e}")

# ----------------- 主服务 -----------------
def tftp_server(cfg, stop_event):
    """
    启动 TFTP Server（阻塞运行，直到 stop_event.set()）
    """
    os.makedirs(cfg.tftp_root, exist_ok=True)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((cfg.bind, cfg.tftp_port))
    s.settimeout(1.0)

    # Windows: 关闭 ICMP“端口不可达”导致的 recvfrom 异常
    if os.name == "nt":
        try:
            SIO_UDP_CONNRESET = 0x9800000C
            s.ioctl(SIO_UDP_CONNRESET, b"\x00\x00\x00\x00")
        except Exception:
            pass

    logging.info(f"TFTP Server on {cfg.bind}:{cfg.tftp_port}, root={cfg.tftp_root}")

    while not stop_event.is_set():
        try:
            data, addr = s.recvfrom(1500)
        except socket.timeout:
            continue
        except Exception as e:
            logging.warning(f"TFTP recv error: {e}")
            continue

        # 仅处理 RRQ：\x00\x01<filename>\x00<mode>\x00[optk]\x00[optv]\x00...
        if len(data) < 4 or data[1] != _TFTP_OP_RRQ:
            continue

        parts = data[2:].split(b"\x00")
        if len(parts) < 2:
            continue

        filename = parts[0].decode(errors="ignore")
        mode = (parts[1] or b"").decode(errors="ignore").lower()

        # 解析 options + 记录顺序
        opts = {}
        order = []
        i = 2
        while i + 1 < len(parts) and parts[i]:
            k = parts[i].decode(errors="ignore").lower()
            v = parts[i + 1].decode(errors="ignore")
            opts[k] = v
            order.append(k)
            i += 2

        path = os.path.join(cfg.tftp_root, filename)
        logging.info(f"TFTP RRQ {addr}: {filename} mode={mode} opts={opts}")

        # 文件不存在：立即返回错误
        if not os.path.exists(path):
            s.sendto(_ERR_NOT_FOUND, addr)
            logging.warning(f"TFTP File not found: {path}")
            continue

        # 识别常见固件
        fn = filename.lower()
        is_bios_stage1 = (fn.endswith("undionly.kpxe"))       # BIOS 第一阶段
        is_uefi_ipxe   = (fn.endswith("ipxe.efi"))            # UEFI 第一阶段（固件 iPXE）

        want_tsize   = "tsize"   in opts
        want_blksize = "blksize" in opts

        # 计算文件大小（给 tsize）
        def _get_size(p):
            try:
                return os.path.getsize(p)
            except Exception:
                return 0

        # ---------- 兼容策略 1：BIOS 首次 RRQ（仅 tsize）→ 只回 OACK(tsize) ----------
        if is_bios_stage1 and want_tsize and not want_blksize:
            size = _get_size(path)
            logging.debug(f"TFTP[{addr}] BIOS stage-1: reply OACK(tsize={size}) only")
            _send_oack(s, addr, [("tsize", size)])
            # 不发送数据，等待客户端第二次 RRQ（会带 blksize）再开始数据流
            continue

        # ---------- 兼容策略 2：UEFI ipxe.efi 首次 RRQ 带 tsize+blksize → 只回 tsize ----------
        if is_uefi_ipxe and want_tsize and want_blksize:
            size = _get_size(path)
            logging.info(f"UEFI ipxe.efi negotiation fix: reply only tsize={size}, skip blksize to avoid abort")
            _send_oack(s, addr, [("tsize", size)])
            # 同上，不发送数据，等待后续仅带 blksize 的 RRQ 再进入数据流
            continue

        # ---------- 正常协商路径 ----------
        # 设置默认块大小
        blksize = 512

        if want_tsize or want_blksize:
            pairs = []
            # 按客户端原始顺序回显（有些固件很挑顺序）
            for k in order:
                if k == "tsize" and want_tsize:
                    pairs.append(("tsize", _get_size(path)))
                elif k == "blksize" and want_blksize:
                    try:
                        blksize = max(8, int(opts.get("blksize", "512")))
                    except Exception:
                        blksize = 512
                    pairs.append(("blksize", blksize))

            # 若客户端只带了其中一项，仍补上
            if not pairs:
                if want_tsize:
                    pairs.append(("tsize", _get_size(path)))
                if want_blksize:
                    try:
                        blksize = max(8, int(opts.get("blksize", "512")))
                    except Exception:
                        blksize = 512
                    pairs.append(("blksize", blksize))

            _send_oack(s, addr, pairs)

            # 这里是“可直接传”的分支（已和客户端约好 blksize）
            # 但客户端可能先回 ACK(0)，所以尝试快速吸收 ACK(0) 再开始 DATA(1)
            _maybe_drain_ack0(s, addr, timeout=0.5)
            _tftp_stream(s, addr, path, blksize)
            continue

        # ---------- 无协商参数：老固件兼容（512 字节） ----------
        _tftp_stream(s, addr, path, blksize=512)

    logging.info("TFTP Server stopped.")
