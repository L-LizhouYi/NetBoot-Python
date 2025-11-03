# Modular PXE / iPXE Server (BIOS + UEFI)

**Features**
- DHCP Proxy: BIOS→`undionly.kpxe`, UEFI→`ipxe.efi`, iPXE→`boot.ipxe`
- TFTP: OACK echo (tsize/blksize), stop-and-wait with retransmission
- HTTP: static files from `srv/http` (ThreadingHTTPServer)
- Auto-pick interface by `--ip` (Windows uses pcap backend)
- Graceful shutdown via SIGINT/SIGTERM

## Run

```bash
python main.py --ip 192.168.73.1 --http 8080 --log-level INFO
```

Place files:
```
srv/
├─ tftp/
│  ├─ undionly.kpxe
│  ├─ ipxe.efi
│  └─ boot.ipxe
└─ http/
   └─ (your images, e.g. /boot/wimboot, /boot/Boot/*, /boot/boot.wim)
```

## Example `boot.ipxe` (BIOS + UEFI WinPE)

```ipxe
#!ipxe
dhcp
set base http://192.168.73.1:8080/boot
iseq ${platform} efi && goto uefi || goto bios

:uefi
kernel ${base}/wimboot
initrd ${base}/BOOTX64.EFI             bootx64.efi
initrd ${base}/Boot/BCD                BCD
initrd ${base}/Boot/boot.sdi           boot.sdi
initrd ${base}/boot.wim                boot.wim
boot

:bios
kernel ${base}/wimboot
initrd ${base}/Boot/pxeboot.n12        pxeboot.n12
initrd ${base}/Boot/BCD                BCD
initrd ${base}/Boot/boot.sdi           boot.sdi
initrd ${base}/boot.wim                boot.wim
initrd ${base}/bootmgr.exe             bootmgr.exe
boot
```
