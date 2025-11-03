from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class Config:
    """Runtime configuration for the PXE/iPXE server stack."""
    server_ip: str
    tftp_port: int = 69
    http_port: int = 8080
    bind: str = "0.0.0.0"
    log_level: str = "INFO"
    iface: Optional[str] = None

    @property
    def base_dir(self) -> str:
        return os.path.dirname(os.path.abspath(__file__))

    @property
    def tftp_root(self) -> str:
        return os.path.join(self.base_dir, "srv", "tftp")

    @property
    def http_root(self) -> str:
        return os.path.join(self.base_dir, "srv", "http")

    # TFTP bootfiles
    @property
    def bootfile_bios(self) -> bytes: return b"undionly.kpxe"
    @property
    def bootfile_uefi(self) -> bytes: return b"ipxe.efi"
    @property
    def bootfile_ipxe(self) -> bytes: return b"boot.ipxe"
