"""
scanners/autorun.py
-------------------
Scanner de entradas de inicialização automática do Windows.
Verifica Registro (HKCU/HKLM Run) e Pastas de Startup.
"""

import os
import winreg

from core.icons import get_icon_base64
from core.utils import resolve_path


class AutorunScanner:
    """
    Audita programas configurados para iniciar automaticamente com o Windows,
    verificando tanto o Registro quanto as pastas de inicialização do sistema.
    """

    REGISTRY_PATHS = [
        (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\Run",         "HKCU\\Run",    "Usuário"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run",         "HKLM\\Run",    "Global"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM\\WOW64", "Global (32-bit)"),
    ]

    @property
    def _folder_paths(self):
        return [
            (
                os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup"),
                "Startup (Usuário)", "Usuário"
            ),
            (
                os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), r"Microsoft\Windows\Start Menu\Programs\Startup"),
                "Startup (Global)", "Global"
            ),
        ]

    def scan(self) -> list[dict]:
        """
        Executa o scan completo e retorna lista de entradas de autorun.

        Returns:
            Lista de dicts com: name, path, resolved_path, location, scope,
            hroot, subkey, exists, type, icon
        """
        results = []
        results.extend(self._scan_registry())
        results.extend(self._scan_folders())
        return results

    def _scan_registry(self) -> list[dict]:
        entries = []
        for hroot, subkey, loc_name, scope in self.REGISTRY_PATHS:
            try:
                with winreg.OpenKey(hroot, subkey, 0, winreg.KEY_READ) as key:
                    idx = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, idx)
                            resolved = resolve_path(value)
                            entries.append({
                                "name":          name,
                                "path":          value,
                                "resolved_path": resolved,
                                "location":      loc_name,
                                "scope":         scope,
                                "hroot":         "HKCU" if hroot == winreg.HKEY_CURRENT_USER else "HKLM",
                                "subkey":        subkey,
                                "exists":        os.path.exists(resolved),
                                "type":          "Registry",
                                "icon":          get_icon_base64(value),
                            })
                            idx += 1
                        except OSError:
                            break
            except Exception:
                pass
        return entries

    def _scan_folders(self) -> list[dict]:
        entries = []
        for folder, loc_name, scope in self._folder_paths:
            if not os.path.isdir(folder):
                continue
            for filename in os.listdir(folder):
                full_path = os.path.join(folder, filename)
                entries.append({
                    "name":          filename,
                    "path":          full_path,
                    "resolved_path": full_path,
                    "location":      loc_name,
                    "scope":         scope,
                    "hroot":         None,
                    "subkey":        None,
                    "exists":        True,
                    "type":          "Folder",
                    "icon":          get_icon_base64(full_path),
                })
        return entries
