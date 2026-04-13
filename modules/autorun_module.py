"""
modules/autorun_module.py
-------------------------
API e HTML do módulo de Auditoria de Inicialização (Autorun).
"""

import os
import sys
import json
import winreg
import datetime
import subprocess
from pathlib import Path

from core.utils import resolve_path
from scanners.autorun import AutorunScanner


class AutorunApi:
    """API exposta ao JavaScript via pywebview para o módulo Autorun."""

    def __init__(self):
        self._scanner = AutorunScanner()
        self._last_results: list[dict] = []
        self._reports_dir = Path(os.path.abspath(sys.argv[0])).parent / "reports"
        self._reports_dir.mkdir(exist_ok=True)

    def start_scan(self) -> list[dict]:
        self._last_results = self._scanner.scan()
        return self._last_results

    def open_folder(self, index: int) -> bool:
        try:
            item = self._last_results[index]
            resolved = resolve_path(item["path"])
            if os.path.exists(resolved):
                subprocess.run(["explorer", "/select,", resolved])
                return True
            parent = str(Path(resolved).parent)
            if os.path.exists(parent):
                subprocess.run(["explorer", parent])
                return True
            return False
        except Exception:
            return False

    def delete_entry(self, index: int) -> bool:
        try:
            item = self._last_results[index]
            if item["type"] == "Registry":
                hroot = (
                    winreg.HKEY_CURRENT_USER
                    if item["hroot"] == "HKCU"
                    else winreg.HKEY_LOCAL_MACHINE
                )
                with winreg.OpenKey(hroot, item["subkey"], 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, item["name"])
                return True
            elif item["type"] == "Folder":
                if os.path.exists(item["path"]):
                    os.remove(item["path"])
                    return True
            return False
        except Exception:
            return False

    def export_report(self) -> str:
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Autorun_{ts}.json"
            filepath = self._reports_dir / filename
            clean = [{k: v for k, v in i.items() if k != "icon"} for i in self._last_results]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"timestamp": ts, "entries": clean}, f, indent=4, ensure_ascii=False)
            return filename
        except Exception:
            return ""


HTML = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Sentinel — Auditoria de Inicialização</title>
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

        header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 18px 32px; border-bottom: 1px solid var(--border);
            background: rgba(12,12,20,0.95); backdrop-filter: blur(20px);
        }
        .header-left { display: flex; align-items: center; gap: 14px; }
        .header-icon { font-size: 22px; }
        .header-title { font-size: 16px; font-weight: 800; letter-spacing: 3px; color: var(--accent); text-transform: uppercase; }
        .header-right { display: flex; gap: 10px; align-items: center; }

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

        .stats-strip { display: flex; gap: 0; border-bottom: 1px solid var(--border); }
        .stat { flex: 1; padding: 12px 32px; display: flex; align-items: center; gap: 10px; border-right: 1px solid var(--border); }
        .stat:last-child { border-right: none; }
        .stat-num { font-size: 22px; font-weight: 800; }
        .stat-label { font-size: 10px; color: var(--dim); text-transform: uppercase; letter-spacing: 1px; }
        .stat-accent { color: var(--accent); }
        .stat-danger { color: var(--danger); }
        .stat-warning { color: var(--warning); }

        main { flex: 1; overflow-y: auto; padding: 20px 32px; }
        main::-webkit-scrollbar { width: 6px; }
        main::-webkit-scrollbar-track { background: transparent; }
        main::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }

        .entry-list { display: flex; flex-direction: column; gap: 8px; }

        .entry {
            background: var(--surf); border: 1px solid var(--border); border-radius: 12px;
            padding: 14px 20px; display: grid;
            grid-template-columns: 44px 1.4fr 2.6fr 110px 90px;
            align-items: center; gap: 16px;
            transition: border-color 0.2s, transform 0.15s;
        }
        .entry:hover { border-color: rgba(0,242,255,0.3); transform: translateX(3px); }
        .entry.missing { border-color: rgba(255,51,102,0.2); }

        .icon-box { width: 40px; height: 40px; background: rgba(0,0,0,0.4); border-radius: 10px; border: 1px solid var(--border); display: flex; align-items: center; justify-content: center; overflow: hidden; }
        .icon-box img { width: 28px; height: 28px; object-fit: contain; }
        .icon-box .fallback { font-size: 18px; }

        .entry-info { overflow: hidden; }
        .entry-name { font-weight: 700; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .entry-loc { font-size: 10px; color: var(--accent); font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px; }

        .path-box {
            font-family: 'JetBrains Mono', monospace; font-size: 11px;
            color: var(--dim); background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.04); border-radius: 6px;
            padding: 7px 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }

        .badge { font-size: 9px; font-weight: 800; padding: 4px 10px; border-radius: 20px; border: 1px solid transparent; text-align: center; text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap; }
        .badge-ok   { border-color: var(--success); color: var(--success); background: rgba(0,232,122,0.07); }
        .badge-fail { border-color: var(--danger);  color: var(--danger);  background: rgba(255,51,102,0.07); }
        .badge-reg  { font-size: 8px; }

        .entry-actions { display: flex; gap: 6px; justify-content: flex-end; }
        .act-btn { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 8px; border: 1px solid var(--border); background: rgba(255,255,255,0.03); cursor: pointer; font-size: 14px; transition: 0.2s; }
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
            <span class="header-icon">🚀</span>
            <span class="header-title">Auditoria de Inicialização</span>
        </div>
        <div class="header-right">
            <button class="btn btn-ghost" onclick="runScan()">↻ Recarregar</button>
            <button class="btn btn-primary" onclick="exportReport()">⬇ Exportar</button>
        </div>
    </header>

    <div class="stats-strip">
        <div class="stat"><span class="stat-num stat-accent" id="st-total">–</span><span class="stat-label">Total</span></div>
        <div class="stat"><span class="stat-num stat-danger" id="st-missing">–</span><span class="stat-label">Arquivo Faltando</span></div>
        <div class="stat"><span class="stat-num stat-warning" id="st-reg">–</span><span class="stat-label">Entradas de Registro</span></div>
        <div class="stat"><span class="stat-num" id="st-folder" style="color:var(--text)">–</span><span class="stat-label">Pastas de Startup</span></div>
    </div>

    <div class="toolbar">
        <div class="search-box">
            <span style="color:var(--dim);font-size:14px">🔍</span>
            <input type="text" id="search" placeholder="Filtrar por nome ou caminho..." oninput="renderList()">
        </div>
        <button class="filter-btn active" data-filter="all" onclick="setFilter('all', this)">Todos</button>
        <button class="filter-btn" data-filter="missing" onclick="setFilter('missing', this)">⚠ Faltando</button>
        <button class="filter-btn" data-filter="registry" onclick="setFilter('registry', this)">Registro</button>
        <button class="filter-btn" data-filter="folder" onclick="setFilter('folder', this)">Pasta</button>
    </div>

    <main>
        <div id="results" class="entry-list"></div>
    </main>

    <script>
        let allData = [];
        let activeFilter = 'all';

        async function runScan() {
            const res = document.getElementById('results');
            res.innerHTML = '<div class="loading"><div class="spinner"></div>VARRENDO SISTEMA...</div>';
            allData = await pywebview.api.start_scan();
            updateStats();
            renderList();
        }

        function updateStats() {
            document.getElementById('st-total').textContent = allData.length;
            document.getElementById('st-missing').textContent = allData.filter(i => !i.exists).length;
            document.getElementById('st-reg').textContent = allData.filter(i => i.type === 'Registry').length;
            document.getElementById('st-folder').textContent = allData.filter(i => i.type === 'Folder').length;
        }

        function setFilter(f, el) {
            activeFilter = f;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            el.classList.add('active');
            renderList();
        }

        function renderList() {
            const query = document.getElementById('search').value.toLowerCase();
            let data = allData;

            if (activeFilter === 'missing')  data = data.filter(i => !i.exists);
            if (activeFilter === 'registry') data = data.filter(i => i.type === 'Registry');
            if (activeFilter === 'folder')   data = data.filter(i => i.type === 'Folder');
            if (query) data = data.filter(i =>
                i.name.toLowerCase().includes(query) || i.path.toLowerCase().includes(query)
            );

            const res = document.getElementById('results');
            if (data.length === 0) {
                res.innerHTML = '<div class="empty-state"><div class="es-icon">✅</div><div class="es-text">Nenhuma entrada encontrada</div></div>';
                return;
            }

            // Map filtered items back to original indices
            const originalIndices = data.map(item => allData.indexOf(item));
            res.innerHTML = '';
            data.forEach((item, fi) => {
                const idx = originalIndices[fi];
                const icon = item.icon
                    ? `<img src="${item.icon}" alt="">`
                    : `<span class="fallback">📄</span>`;
                const row = document.createElement('div');
                row.className = 'entry' + (item.exists ? '' : ' missing');
                row.innerHTML = `
                    <div class="icon-box">${icon}</div>
                    <div class="entry-info">
                        <div class="entry-name" title="${item.name}">${item.name}</div>
                        <div class="entry-loc">${item.location}</div>
                    </div>
                    <div class="path-box" title="${item.path}">${item.path}</div>
                    <div><span class="badge ${item.exists ? 'badge-ok' : 'badge-fail'}">${item.exists ? 'Verificado' : 'Faltando'}</span></div>
                    <div class="entry-actions">
                        <button class="act-btn" title="Abrir no Explorer" onclick="openFolder(${idx})">📂</button>
                        <button class="act-btn danger" title="Remover entrada" onclick="confirmDelete(${idx}, '${item.name.replace(/'/g,'\\'')}')">🗑</button>
                    </div>`;
                res.appendChild(row);
            });
        }

        async function openFolder(idx) { await pywebview.api.open_folder(idx); }

        async function confirmDelete(idx, name) {
            if (confirm(`Remover "${name}" do sistema?`)) {
                if (await pywebview.api.delete_entry(idx)) runScan();
                else alert('Falha ao remover. Certifique-se de estar rodando como Administrador.');
            }
        }

        async function exportReport() {
            const fn = await pywebview.api.export_report();
            if (fn) alert('Relatório salvo em:\\nreports\\\\' + fn);
            else alert('Erro ao exportar relatório.');
        }

        window.addEventListener('pywebviewready', runScan);
    </script>
</body>
</html>"""
