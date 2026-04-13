"""
core/utils.py
-------------
Funções utilitárias compartilhadas entre todos os módulos do Sentinel.
Elimina duplicação de hide_console, is_admin, run_as_admin, resolve_path.
"""

import os
import sys
import re
import ctypes


def hide_console():
    """Oculta a janela do console (cmd/PowerShell) no Windows."""
    try:
        kernel32 = ctypes.WinDLL('kernel32')
        user32 = ctypes.WinDLL('user32')
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            user32.ShowWindow(hwnd, 0)
    except Exception:
        pass


def is_admin() -> bool:
    """Retorna True se o processo está rodando com privilégios de administrador."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_as_admin():
    """
    Reinicia o processo atual com privilégios elevados via UAC.
    Encerra o processo atual se não for admin.
    """
    if not is_admin():
        script = os.path.abspath(sys.argv[0])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}"', None, 1
        )
        sys.exit()


def show_error_popup(message: str, title: str = "Sentinel — Erro Crítico"):
    """Exibe uma MessageBox de erro no Windows."""
    try:
        ctypes.windll.user32.MessageBoxW(0, str(message), title, 0x10)
    except Exception:
        print(f"[ERRO] {title}: {message}")


def resolve_path(raw_path: str) -> str:
    """
    Normaliza um caminho de executável vindo do Registro ou de comandos,
    expandindo variáveis de ambiente e removendo aspas e argumentos extras.
    """
    if not raw_path:
        return ""

    clean = raw_path.strip()

    # Expandir variáveis de ambiente (%SystemRoot%, %AppData%, etc.)
    try:
        clean = os.path.expandvars(clean)
    except Exception:
        pass

    # Caso com aspas: "C:\path\app.exe" /arg
    if clean.startswith('"'):
        match = re.search(r'"(.*?)"', clean)
        if match:
            clean = match.group(1)
        else:
            clean = clean.lstrip('"').split('"')[0]
    else:
        # Sem aspas: C:\path\app.exe /arg ou system32\svchost.exe
        executable_match = re.search(
            r'(.*?\.(?:exe|dll|bat|cmd|lnk|vbs|ps1))', clean, re.IGNORECASE
        )
        if executable_match:
            clean = executable_match.group(1)
        else:
            clean = clean.split(' ')[0]

    return clean.strip()


def get_machine_info() -> dict:
    """Retorna informações básicas sobre a máquina atual."""
    return {
        "computer": os.environ.get("COMPUTERNAME", "Unknown"),
        "user": os.environ.get("USERNAME", "Unknown"),
        "is_admin": is_admin(),
    }
