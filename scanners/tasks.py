"""
scanners/tasks.py
-----------------
Auditor de Tarefas Agendadas do Windows via PowerShell.
"""

import json
import subprocess

from core.icons import get_icon_base64
from core.utils import resolve_path


class TasksScanner:
    """
    Enumera todas as tarefas agendadas do sistema usando Get-ScheduledTask.
    """

    def scan(self) -> list[dict]:
        """
        Retorna lista de tarefas agendadas.

        Returns:
            Lista de dicts com: name, path, state, action, icon
        """
        cmd = (
            'Get-ScheduledTask | '
            'Select-Object TaskName, TaskPath, State, '
            '@{Name="Action";Expression={($_.Actions.Execute -join ", ")}} | '
            'ConvertTo-Json'
        )
        try:
            output = subprocess.check_output(
                ["powershell", "-Command", cmd],
                stderr=subprocess.STDOUT,
            ).decode("utf-8", errors="ignore")

            data = json.loads(output)
            if isinstance(data, dict):
                data = [data]

            results = []
            for task in data:
                action = task.get("Action") or ""
                results.append({
                    "name":   task.get("TaskName") or "Tarefa Desconhecida",
                    "path":   task.get("TaskPath") or "\\",
                    "state":  task.get("State") or "Unknown",
                    "action": action,
                    "icon":   get_icon_base64(action),
                })
            return results
        except Exception:
            return []
