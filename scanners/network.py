"""
scanners/network.py
-------------------
Monitor de conexões TCP ativas em tempo real via Windows IP Helper API.
Usa GetExtendedTcpTable para obter conexões com PID do processo dono.
"""

import os
import json
import socket
import struct
import ctypes
import subprocess
from ctypes import wintypes

from core.icons import get_icon_base64
from core.utils import resolve_path

# --- Constantes WinAPI ---
AF_INET               = 2
TCP_TABLE_OWNER_PID_ALL = 5

TCP_STATES = {
    1: "CLOSED",     2: "LISTENING",  3: "SYN_SENT",
    4: "SYN_RCVD",  5: "ESTABLISHED", 6: "FIN_WAIT1",
    7: "FIN_WAIT2",  8: "CLOSE_WAIT", 9: "CLOSING",
    10: "LAST_ACK", 11: "TIME_WAIT",  12: "DELETE_TCB",
}


# --- Estruturas WinAPI ---
class MIB_TCPROW_OWNER_PID(ctypes.Structure):
    _fields_ = [
        ("dwState",      wintypes.DWORD),
        ("dwLocalAddr",  wintypes.DWORD),
        ("dwLocalPort",  wintypes.DWORD),
        ("dwRemoteAddr", wintypes.DWORD),
        ("dwRemotePort", wintypes.DWORD),
        ("dwOwningPid",  wintypes.DWORD),
    ]


class MIB_TCPTABLE_OWNER_PID(ctypes.Structure):
    _fields_ = [
        ("dwNumEntries", wintypes.DWORD),
        ("table",        MIB_TCPROW_OWNER_PID * 1),
    ]


def _decode_port(port_val: int) -> int:
    return socket.ntohs(port_val & 0xFFFF)


def _decode_ip(ip_val: int) -> str:
    return socket.inet_ntoa(struct.pack("<L", ip_val))


class _ProcessMetadataCache:
    """Cache de metadados de processos (PID → nome, path) via PowerShell."""

    def __init__(self):
        self._cache: dict[int, tuple[str, str]] = {}

    def refresh(self):
        new_cache: dict[int, tuple[str, str]] = {}
        try:
            cmd = "Get-Process | Select-Object Id, Name, Path | ConvertTo-Json"
            output = subprocess.check_output(
                ["powershell", "-Command", cmd],
                stderr=subprocess.STDOUT,
            ).decode("utf-8", errors="ignore")
            data = json.loads(output)
            if isinstance(data, dict):
                data = [data]
            for proc in data:
                pid = proc.get("Id")
                if pid:
                    new_cache[pid] = (
                        proc.get("Name", "Unknown"),
                        proc.get("Path") or "",
                    )
        except Exception:
            pass
        self._cache = new_cache

    def get(self, pid: int) -> tuple[str, str]:
        if pid == 0:
            return "System Idle Process", ""
        if pid == 4:
            return "System", r"C:\Windows\System32\ntoskrnl.exe"
        return self._cache.get(pid, (f"PID:{pid}", ""))


class NetworkScanner:
    """
    Obtém todas as conexões TCP IPv4 ativas e as associa ao processo dono.
    """

    def __init__(self):
        self._proc_cache = _ProcessMetadataCache()

    def get_connections(self) -> list[dict]:
        """
        Retorna lista de conexões TCP ativas.

        Returns:
            Lista de dicts com: proto, local, remote, state, pid, process, path, icon
        """
        self._proc_cache.refresh()
        connections = []

        size = wintypes.DWORD(0)
        ctypes.windll.iphlpapi.GetExtendedTcpTable(
            None, ctypes.byref(size), True, AF_INET, TCP_TABLE_OWNER_PID_ALL, 0
        )
        buf = (ctypes.c_byte * size.value)()

        result = ctypes.windll.iphlpapi.GetExtendedTcpTable(
            buf, ctypes.byref(size), True, AF_INET, TCP_TABLE_OWNER_PID_ALL, 0
        )
        if result != 0:
            return connections

        table = ctypes.cast(buf, ctypes.POINTER(MIB_TCPTABLE_OWNER_PID)).contents
        entries = ctypes.cast(
            ctypes.addressof(table.table),
            ctypes.POINTER(MIB_TCPROW_OWNER_PID)
        )

        for i in range(table.dwNumEntries):
            row = entries[i]
            name, path = self._proc_cache.get(row.dwOwningPid)
            connections.append({
                "proto":   "TCP",
                "local":   f"{_decode_ip(row.dwLocalAddr)}:{_decode_port(row.dwLocalPort)}",
                "remote":  f"{_decode_ip(row.dwRemoteAddr)}:{_decode_port(row.dwRemotePort)}",
                "state":   TCP_STATES.get(row.dwState, "UNKNOWN"),
                "pid":     row.dwOwningPid,
                "process": name,
                "path":    path,
                "icon":    get_icon_base64(path),
            })

        return connections
