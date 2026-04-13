"""
scanners/dns.py
---------------
Scanner de configurações DNS e arquivo Hosts do Windows.
Lê DNS via Registro e retorna conteúdo do arquivo hosts.
"""

import os
import winreg
import subprocess
import json


HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"


class DNSScanner:
    """
    Coleta configurações de servidores DNS e conteúdo do arquivo Hosts.
    """

    def get_dns_settings(self) -> list[dict]:
        """
        Lê servidores DNS de todas as interfaces via Registro do Windows.

        Returns:
            Lista de dicts com: interface, servers, is_google, is_cloudflare
        """
        dns_servers = []
        reg_path = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as root_key:
                idx = 0
                while True:
                    try:
                        iface_name = winreg.EnumKey(root_key, idx)
                        with winreg.OpenKey(root_key, iface_name) as subkey:
                            servers = ""
                            try:
                                servers, _ = winreg.QueryValueEx(subkey, "NameServer")
                            except FileNotFoundError:
                                pass
                            if not servers:
                                try:
                                    servers, _ = winreg.QueryValueEx(subkey, "DhcpNameServer")
                                except FileNotFoundError:
                                    pass
                            if servers:
                                dns_servers.append({
                                    "interface":     iface_name,
                                    "servers":       servers,
                                    "is_google":     "8.8.8.8" in servers or "8.8.4.4" in servers,
                                    "is_cloudflare": "1.1.1.1" in servers or "1.0.0.1" in servers,
                                })
                        idx += 1
                    except OSError:
                        break
        except Exception:
            pass
        return dns_servers

    def get_dns_via_powershell(self) -> list[dict]:
        """
        Alternativa: lê DNS via Get-DnsClientServerAddress (mais detalhado).
        """
        try:
            cmd = (
                "Get-DnsClientServerAddress -AddressFamily IPv4 | "
                "Select-Object InterfaceAlias, ServerAddresses | ConvertTo-Json"
            )
            output = subprocess.check_output(
                ["powershell", "-Command", cmd],
                stderr=subprocess.STDOUT,
            ).decode("utf-8", errors="ignore")
            data = json.loads(output)
            return [data] if isinstance(data, dict) else data
        except Exception:
            return []

    def get_hosts_content(self) -> list[dict]:
        """
        Lê e parseia o arquivo hosts do Windows.

        Returns:
            Lista de dicts com: raw, ip, host, is_comment
        """
        try:
            with open(HOSTS_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
            entries = []
            for line in lines:
                clean = line.strip()
                if not clean:
                    continue
                is_comment = clean.startswith("#")
                parts = clean.split()
                if is_comment or len(parts) < 2:
                    entries.append({"raw": clean, "ip": "", "host": clean, "is_comment": True})
                else:
                    entries.append({
                        "raw":        clean,
                        "ip":         parts[0],
                        "host":       " ".join(parts[1:]),
                        "is_comment": False,
                    })
            return entries
        except Exception:
            return []

    def get_hosts_raw(self) -> str:
        """Retorna o conteúdo bruto do arquivo hosts."""
        try:
            with open(HOSTS_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return "Erro ao ler arquivo hosts."

    def save_hosts(self, content: str) -> bool:
        """
        Grava novo conteúdo no arquivo hosts (requer privilégios admin).
        Cria backup automático na primeira escrita.
        """
        backup = HOSTS_PATH + ".bak"
        try:
            if not os.path.exists(backup):
                import shutil
                shutil.copy2(HOSTS_PATH, backup)
            with open(HOSTS_PATH, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            return False
