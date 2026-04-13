"""
modules/network_module.py
-------------------------
API e HTML do módulo Network Pulse — monitor de conexões TCP em tempo real.
"""

import os
import sys
import json
import datetime
import subprocess
from pathlib import Path

from scanners.network import NetworkScanner


class NetworkApi:
    """API exposta ao JavaScript via pywebview para o módulo Network Pulse."""

    def __init__(self):
        self._scanner = NetworkScanner()
        self._last_results: list[dict] = []
        self._reports_dir = Path(os.path.abspath(sys.argv[0])).parent / "reports"
        self._reports_dir.mkdir(exist_ok=True)

    def get_connections(self) -> list[dict]:
        self._last_results = self._scanner.get_connections()
        return self._last_results

    def kill_process(self, pid: int) -> bool:
        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                check=True, capture_output=True
            )
            return True
        except Exception:
            return False

    def open_folder(self, index: int) -> bool:
        try:
            item = self._last_results[index]
            path = item.get("path", "")
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
            filename = f"Network_{ts}.json"
            filepath = self._reports_dir / filename
            clean = [{k: v for k, v in i.items() if k != "icon"} for i in self._last_results]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"timestamp": ts, "connections": clean}, f, indent=4)
            return filename
        except Exception:
            return ""


HTML = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Sentinel — Network Pulse</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #030305; --surf: #0c0c14; --surf2: #121220;
            --accent: #00f2ff; --accent-dim: rgba(0,242,255,0.12);
            --border: #1e1e2e; --text: #e2e2e9; --dim: #6b6b7a;
            --danger: #ff3366; --success: #00e87a;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: var(--bg); color: var(--text); font-family: 'Outfit', sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }

        header { display: flex; align-items: center; justify-content: space-between; padding: 18px 32px; border-bottom: 1px solid var(--border); background: rgba(12,12,20,0.95); backdrop-filter: blur(20px); }
        .header-left { display: flex; align-items: center; gap: 14px; }
        .header-title { font-size: 16px; font-weight: 800; letter-spacing: 3px; color: var(--accent); text-transform: uppercase; }
        .header-right { display: flex; gap: 10px; align-items: center; }
        .live-dot { width: 8px; height: 8px; background: var(--success); border-radius: 50%; animation: pulse 1.5s ease-in-out infinite; }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }
        .live-label { font-size: 10px; color: var(--success); font-weight: 700; letter-spacing: 2px; }

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

        main { flex: 1; overflow-y: auto; padding: 0; }
        main::-webkit-scrollbar { width: 6px; }
        main::-webkit-scrollbar-track { background: transparent; }
        main::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }

        table { width: 100%; border-collapse: collapse; }
        thead { position: sticky; top: 0; z-index: 10; }
        thead tr { background: var(--surf); border-bottom: 2px solid var(--border); }
        th { padding: 12px 16px; font-size: 10px; font-weight: 700; color: var(--dim); text-transform: uppercase; letter-spacing: 2px; text-align: left; white-space: nowrap; }

        tbody tr { border-bottom: 1px solid var(--border); transition: background 0.15s; }
        tbody tr:hover { background: rgba(255,255,255,0.02); }
        td { padding: 12px 16px; font-size: 13px; vertical-align: middle; }

        .proc-cell { display: flex; align-items: center; gap: 10px; }
        .proc-icon { width: 28px; height: 28px; background: rgba(0,0,0,0.4); border-radius: 7px; border: 1px solid var(--border); display: flex; align-items: center; justify-content: center; overflow: hidden; flex-shrink: 0; }
        .proc-icon img { width: 20px; height: 20px; object-fit: contain; }
        .proc-name { font-weight: 700; color: var(--accent); }
        .proc-pid { font-size: 10px; color: var(--dim); font-family: 'JetBrains Mono', monospace; }

        .addr-text { font-family: 'JetBrains Mono', monospace; font-size: 12px; }

        .state-badge { font-size: 9px; font-weight: 800; padding: 3px 9px; border-radius: 20px; border: 1px solid; text-transform: uppercase; white-space: nowrap; }
        .state-ESTABLISHED { border-color: var(--success); color: var(--success); background: rgba(0,232,122,0.08); }
        .state-LISTENING    { border-color: #ffaa00; color: #ffaa00; background: rgba(255,170,0,0.08); }
        .state-default      { border-color: var(--border); color: var(--dim); }

        .act-btn { width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center; border-radius: 7px; border: 1px solid var(--border); background: rgba(255,255,255,0.03); cursor: pointer; font-size: 13px; transition: 0.2s; margin-left: 5px; }
        .act-btn:hover { border-color: var(--accent); background: var(--accent-dim); }
        .act-btn.danger:hover { border-color: var(--danger); background: rgba(255,51,102,0.1); }

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
            <span style="font-size:22px">📡</span>
            <span class="header-title">Network Pulse</span>
            <div class="live-dot"></div>
            <span class="live-label">AUTO-REFRESH 5s</span>
        </div>
        <div class="header-right">
            <button class="btn btn-ghost" onclick="refresh()">↻ Agora</button>
            <button class="btn btn-primary" onclick="exportReport()">⬇ Exportar</button>
        </div>
    </header>

    <div class="stats-strip">
        <div class="stat"><span class="stat-num" id="st-total" style="color:var(--accent)">–</span><span class="stat-label">Conexões</span></div>
        <div class="stat"><span class="stat-num" id="st-estab" style="color:var(--success)">–</span><span class="stat-label">Established</span></div>
        <div class="stat"><span class="stat-num" id="st-list" style="color:#ffaa00">–</span><span class="stat-label">Listening</span></div>
        <div class="stat"><span class="stat-num" id="st-procs" style="color:var(--text)">–</span><span class="stat-label">Processos</span></div>
    </div>

    <div class="toolbar">
        <div class="search-box">
            <span style="color:var(--dim);font-size:14px">🔍</span>
            <input type="text" id="search" placeholder="Filtrar por processo, IP ou porta..." oninput="renderTable()">
        </div>
        <button class="filter-btn active" onclick="setFilter('all', this)">Todos</button>
        <button class="filter-btn" onclick="setFilter('established', this)">Established</button>
        <button class="filter-btn" onclick="setFilter('listening', this)">Listening</button>
        <button class="filter-btn" onclick="setFilter('external', this)">Externos</button>
    </div>

    <main>
        <div id="results"></div>
    </main>

    <script>
        let allData = [];
        let activeFilter = 'all';
        let refreshTimer = null;

        async function refresh() {
            allData = await pywebview.api.get_connections();
            updateStats();
            renderTable();
        }

        function updateStats() {
            const procs = new Set(allData.map(c => c.pid)).size;
            document.getElementById('st-total').textContent = allData.length;
            document.getElementById('st-estab').textContent = allData.filter(c => c.state === 'ESTABLISHED').length;
            document.getElementById('st-list').textContent  = allData.filter(c => c.state === 'LISTENING').length;
            document.getElementById('st-procs').textContent = procs;
        }

        function setFilter(f, el) {
            activeFilter = f;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            el.classList.add('active');
            renderTable();
        }

        function renderTable() {
            const query = document.getElementById('search').value.toLowerCase();
            let data = allData;
            if (activeFilter === 'established') data = data.filter(c => c.state === 'ESTABLISHED');
            if (activeFilter === 'listening')   data = data.filter(c => c.state === 'LISTENING');
            if (activeFilter === 'external')    data = data.filter(c => !c.remote.startsWith('0.0.0.0') && !c.remote.startsWith('127.'));
            if (query) data = data.filter(c =>
                c.process.toLowerCase().includes(query) ||
                c.local.includes(query) || c.remote.includes(query)
            );

            const originalIndices = data.map(item => allData.indexOf(item));
            const container = document.getElementById('results');
            if (data.length === 0) {
                container.innerHTML = '<div class="empty-state"><div class="es-icon">📡</div><div class="es-text">Nenhuma conexão encontrada</div></div>';
                return;
            }
            const stateClass = s => ['ESTABLISHED','LISTENING'].includes(s) ? `state-${s}` : 'state-default';
            container.innerHTML = `
                <table>
                    <thead><tr>
                        <th>Processo / PID</th>
                        <th>Endereço Local</th>
                        <th>Endereço Remoto</th>
                        <th>Estado</th>
                        <th>Ações</th>
                    </tr></thead>
                    <tbody id="tbl-body"></tbody>
                </table>`;
            const tbody = document.getElementById('tbl-body');
            data.forEach((conn, fi) => {
                const idx = originalIndices[fi];
                const icon = conn.icon
                    ? `<img src="${conn.icon}" alt="">`
                    : `<span style="font-size:14px">🔲</span>`;
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><div class="proc-cell"><div class="proc-icon">${icon}</div><div><div class="proc-name">${conn.process}</div><div class="proc-pid">PID: ${conn.pid}</div></div></div></td>
                    <td><span class="addr-text">${conn.local}</span></td>
                    <td><span class="addr-text">${conn.remote}</span></td>
                    <td><span class="state-badge ${stateClass(conn.state)}">${conn.state}</span></td>
                    <td>
                        <button class="act-btn" title="Abrir no Explorer" onclick="openFolder(${idx})">📂</button>
                        <button class="act-btn danger" title="Encerrar processo" onclick="confirmKill(${conn.pid}, '${conn.process}')">💀</button>
                    </td>`;
                tbody.appendChild(tr);
            });
        }

        async function openFolder(idx) { await pywebview.api.open_folder(idx); }
        async function confirmKill(pid, name) {
            if (confirm(`Encerrar "${name}" (PID ${pid})?`)) {
                if (await pywebview.api.kill_process(pid)) refresh();
            }
        }
        async function exportReport() {
            const fn = await pywebview.api.export_report();
            if (fn) alert('Relatório salvo em:\\nreports\\\\' + fn);
        }

        window.addEventListener('pywebviewready', () => {
            refresh();
            refreshTimer = setInterval(refresh, 5000);
        });
    </script>
</body>
</html>"""
