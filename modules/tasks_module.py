"""
modules/tasks_module.py
-----------------------
API e HTML do módulo TaskGuard — auditoria de tarefas agendadas.
"""

import os
import sys
import json
import datetime
import subprocess
from pathlib import Path

from core.utils import resolve_path
from scanners.tasks import TasksScanner


class TasksApi:
    """API exposta ao JavaScript via pywebview para o módulo TaskGuard."""

    def __init__(self):
        self._scanner = TasksScanner()
        self._last_results: list[dict] = []
        self._reports_dir = Path(os.path.abspath(sys.argv[0])).parent / "reports"
        self._reports_dir.mkdir(exist_ok=True)

    def start_scan(self) -> list[dict]:
        self._last_results = self._scanner.scan()
        return self._last_results

    def toggle_task(self, index: int, enable: bool) -> bool:
        try:
            task = self._last_results[index]
            verb = "Enable" if enable else "Disable"
            cmd = f'{verb}-ScheduledTask -TaskName "{task["name"]}" -TaskPath "{task["path"]}"'
            subprocess.run(["powershell", "-Command", cmd], check=True, capture_output=True)
            return True
        except Exception:
            return False

    def delete_task(self, index: int) -> bool:
        task = self._last_results[index]
        name = task["name"].replace("'", "''")
        path = task["path"]
        methods = [
            ["powershell", "-Command", f"Get-ScheduledTask -TaskName '{name}' | Unregister-ScheduledTask -Confirm:$false"],
            ["schtasks", "/delete", "/tn", task["name"], "/f"],
            ["powershell", "-Command", f"Unregister-ScheduledTask -TaskName '{name}' -Confirm:$false"],
        ]
        for cmd in methods:
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                return True
            except Exception:
                continue
        return False

    def open_folder(self, index: int) -> bool:
        try:
            action = self._last_results[index].get("action", "")
            path = resolve_path(action)
            if path and os.path.exists(path):
                subprocess.run(["explorer", "/select,", path])
                return True
            parent = str(Path(path).parent) if path else ""
            if parent and os.path.exists(parent):
                subprocess.run(["explorer", parent])
                return True
            return False
        except Exception:
            return False

    def export_report(self) -> str:
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Tasks_{ts}.json"
            filepath = self._reports_dir / filename
            clean = [{k: v for k, v in i.items() if k != "icon"} for i in self._last_results]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"timestamp": ts, "tasks": clean}, f, indent=4, ensure_ascii=False)
            return filename
        except Exception:
            return ""


HTML = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Sentinel — TaskGuard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #030305; --surf: #0c0c14; --surf2: #121220;
            --accent: #00f2ff; --accent-dim: rgba(0,242,255,0.12);
            --border: #1e1e2e; --text: #e2e2e9; --dim: #6b6b7a;
            --danger: #ff3366; --success: #00e87a; --warning: #ffaa00;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: var(--bg); color: var(--text); font-family: 'Outfit', sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        header { display: flex; align-items: center; justify-content: space-between; padding: 18px 32px; border-bottom: 1px solid var(--border); background: rgba(12,12,20,0.95); backdrop-filter: blur(20px); }
        .header-left { display: flex; align-items: center; gap: 14px; }
        .header-title { font-size: 16px; font-weight: 800; letter-spacing: 3px; color: var(--accent); text-transform: uppercase; }
        .header-right { display: flex; gap: 10px; }
        .btn { display: flex; align-items: center; gap: 7px; padding: 8px 18px; border-radius: 8px; font-weight: 700; font-size: 11px; letter-spacing: 1px; text-transform: uppercase; cursor: pointer; border: none; transition: all 0.2s; font-family: 'Outfit', sans-serif; }
        .btn-primary { background: var(--accent); color: #000; }
        .btn-primary:hover { filter: brightness(1.15); box-shadow: 0 0 20px rgba(0,242,255,0.35); }
        .btn-ghost { background: transparent; border: 1px solid var(--border); color: var(--dim); }
        .btn-ghost:hover { border-color: var(--accent); color: var(--accent); }

        .toolbar { padding: 14px 32px; display: flex; align-items: center; gap: 12px; border-bottom: 1px solid var(--border); background: var(--surf); }
        .search-box { flex: 1; display: flex; align-items: center; gap: 10px; background: var(--surf2); border: 1px solid var(--border); border-radius: 8px; padding: 8px 14px; }
        .search-box input { background: none; border: none; outline: none; color: var(--text); font-family: 'Outfit', sans-serif; font-size: 13px; width: 100%; }
        .search-box input::placeholder { color: var(--dim); }
        .filter-btn { padding: 7px 14px; border-radius: 7px; font-size: 11px; font-weight: 700; cursor: pointer; border: 1px solid var(--border); background: transparent; color: var(--dim); text-transform: uppercase; letter-spacing: 1px; transition: 0.2s; font-family: 'Outfit', sans-serif; }
        .filter-btn.active { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }

        .stats-strip { display: flex; border-bottom: 1px solid var(--border); }
        .stat { flex: 1; padding: 12px 32px; display: flex; align-items: center; gap: 10px; border-right: 1px solid var(--border); }
        .stat:last-child { border-right: none; }
        .stat-num { font-size: 22px; font-weight: 800; }
        .stat-label { font-size: 10px; color: var(--dim); text-transform: uppercase; letter-spacing: 1px; }

        main { flex: 1; overflow-y: auto; padding: 20px 32px; }
        main::-webkit-scrollbar { width: 6px; }
        main::-webkit-scrollbar-track { background: transparent; }
        main::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }

        .task-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 14px; }

        .task-card { background: var(--surf); border: 1px solid var(--border); border-radius: 14px; padding: 18px 20px; transition: border-color 0.2s, transform 0.15s; }
        .task-card:hover { border-color: rgba(0,242,255,0.3); transform: translateY(-2px); }
        .task-card.disabled-task { opacity: 0.55; }

        .card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
        .task-icon { width: 38px; height: 38px; background: rgba(0,0,0,0.4); border-radius: 10px; border: 1px solid var(--border); display: flex; align-items: center; justify-content: center; overflow: hidden; flex-shrink: 0; }
        .task-icon img { width: 26px; height: 26px; object-fit: contain; }
        .task-name { font-weight: 700; font-size: 14px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .state-badge { font-size: 9px; font-weight: 800; padding: 3px 9px; border-radius: 20px; border: 1px solid; text-transform: uppercase; white-space: nowrap; flex-shrink: 0; }
        .state-Ready    { border-color: var(--success); color: var(--success); background: rgba(0,232,122,0.08); }
        .state-Disabled { border-color: var(--dim);     color: var(--dim);     background: transparent; }
        .state-Running  { border-color: var(--warning);  color: var(--warning);  background: rgba(255,170,0,0.08); }
        .state-Unknown  { border-color: var(--border);   color: var(--dim); }

        .task-path { font-size: 10px; color: var(--dim); margin-bottom: 10px; font-family: 'JetBrains Mono', monospace; }
        .action-box { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.04); border-radius: 7px; padding: 8px 11px; font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

        .card-actions { display: flex; gap: 8px; margin-top: 14px; border-top: 1px solid var(--border); padding-top: 12px; }
        .card-btn { flex: 1; padding: 7px; border-radius: 8px; border: 1px solid var(--border); background: rgba(255,255,255,0.03); cursor: pointer; font-size: 11px; font-weight: 700; color: var(--dim); text-align: center; transition: 0.2s; font-family: 'Outfit', sans-serif; }
        .card-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-dim); }
        .card-btn.danger:hover { border-color: var(--danger); color: var(--danger); background: rgba(255,51,102,0.08); }

        .empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; gap: 16px; color: var(--dim); }
        .empty-state .es-icon { font-size: 48px; opacity: 0.3; }
        .empty-state .es-text { font-size: 14px; letter-spacing: 2px; text-transform: uppercase; }
        .loading { display: flex; align-items: center; justify-content: center; gap: 12px; height: 300px; color: var(--accent); font-weight: 700; letter-spacing: 2px; }
        .spinner { width: 24px; height: 24px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <header>
        <div class="header-left">
            <span style="font-size:22px">📅</span>
            <span class="header-title">TaskGuard</span>
        </div>
        <div class="header-right">
            <button class="btn btn-ghost" onclick="runScan()">↻ Recarregar</button>
            <button class="btn btn-primary" onclick="exportReport()">⬇ Exportar</button>
        </div>
    </header>

    <div class="stats-strip">
        <div class="stat"><span class="stat-num" id="st-total" style="color:var(--accent)">–</span><span class="stat-label">Total</span></div>
        <div class="stat"><span class="stat-num" id="st-ready" style="color:var(--success)">–</span><span class="stat-label">Ativas (Ready)</span></div>
        <div class="stat"><span class="stat-num" id="st-disabled" style="color:var(--dim)">–</span><span class="stat-label">Desativadas</span></div>
        <div class="stat"><span class="stat-num" id="st-running" style="color:var(--warning)">–</span><span class="stat-label">Rodando Agora</span></div>
    </div>

    <div class="toolbar">
        <div class="search-box">
            <span style="color:var(--dim);font-size:14px">🔍</span>
            <input type="text" id="search" placeholder="Filtrar por nome ou ação..." oninput="renderCards()">
        </div>
        <button class="filter-btn active" onclick="setFilter('all', this)">Todos</button>
        <button class="filter-btn" onclick="setFilter('ready', this)">Ativos</button>
        <button class="filter-btn" onclick="setFilter('disabled', this)">Desativados</button>
        <button class="filter-btn" onclick="setFilter('running', this)">Rodando</button>
    </div>

    <main>
        <div id="results"></div>
    </main>

    <script>
        let allData = [];
        let activeFilter = 'all';

        async function runScan() {
            document.getElementById('results').innerHTML = '<div class="loading"><div class="spinner"></div>CARREGANDO TAREFAS...</div>';
            allData = await pywebview.api.start_scan();
            updateStats();
            renderCards();
        }

        function updateStats() {
            document.getElementById('st-total').textContent    = allData.length;
            document.getElementById('st-ready').textContent    = allData.filter(t => t.state === 'Ready').length;
            document.getElementById('st-disabled').textContent = allData.filter(t => t.state === 'Disabled').length;
            document.getElementById('st-running').textContent  = allData.filter(t => t.state === 'Running').length;
        }

        function setFilter(f, el) {
            activeFilter = f;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            el.classList.add('active');
            renderCards();
        }

        function renderCards() {
            const query = document.getElementById('search').value.toLowerCase();
            let data = allData;
            if (activeFilter === 'ready')    data = data.filter(t => t.state === 'Ready');
            if (activeFilter === 'disabled') data = data.filter(t => t.state === 'Disabled');
            if (activeFilter === 'running')  data = data.filter(t => t.state === 'Running');
            if (query) data = data.filter(t =>
                t.name.toLowerCase().includes(query) || (t.action || '').toLowerCase().includes(query)
            );

            const originalIndices = data.map(item => allData.indexOf(item));
            const container = document.getElementById('results');
            if (data.length === 0) {
                container.innerHTML = '<div class="empty-state"><div class="es-icon">📅</div><div class="es-text">Nenhuma tarefa encontrada</div></div>';
                return;
            }

            container.innerHTML = '<div class="task-grid" id="task-grid"></div>';
            const grid = document.getElementById('task-grid');
            data.forEach((task, fi) => {
                const idx = originalIndices[fi];
                const isActive = task.state === 'Ready' || task.state === 'Running';
                const icon = task.icon ? `<img src="${task.icon}" alt="">` : '📄';
                const stateClass = `state-${task.state}` ;
                const card = document.createElement('div');
                card.className = 'task-card' + (task.state === 'Disabled' ? ' disabled-task' : '');
                card.innerHTML = `
                    <div class="card-header">
                        <div class="task-icon">${icon}</div>
                        <div class="task-name" title="${task.name}">${task.name}</div>
                        <span class="state-badge ${stateClass}">${task.state}</span>
                    </div>
                    <div class="task-path">${task.path}</div>
                    <div class="action-box" title="${task.action || ''}">${task.action || '(sem ação definida)'}</div>
                    <div class="card-actions">
                        <button class="card-btn" onclick="openFolder(${idx})">📂 Abrir</button>
                        <button class="card-btn" onclick="toggleTask(${idx}, ${!isActive})">${isActive ? '⏸ Desativar' : '▶ Ativar'}</button>
                        <button class="card-btn danger" onclick="deleteTask(${idx}, '${task.name.replace(/'/g,"\\'")}')">🗑 Deletar</button>
                    </div>`;
                grid.appendChild(card);
            });
        }

        async function openFolder(idx) { await pywebview.api.open_folder(idx); }
        async function toggleTask(idx, enable) {
            if (await pywebview.api.toggle_task(idx, enable)) runScan();
        }
        async function deleteTask(idx, name) {
            if (confirm(`Deletar tarefa "${name}" permanentemente?`)) {
                if (await pywebview.api.delete_task(idx)) runScan();
                else alert('Falha ao deletar. Tente como Administrador.');
            }
        }
        async function exportReport() {
            const fn = await pywebview.api.export_report();
            if (fn) alert('Relatório salvo em:\\nreports\\\\' + fn);
        }

        window.addEventListener('pywebviewready', runScan);
    </script>
</body>
</html>"""
