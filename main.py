"""
main.py
-------
Sentinel Audit Suite — Entry Point
Hub central que orquestra todos os módulos de auditoria de segurança.

Uso:
    python main.py          (requer privilégios de Administrador)
"""

import os
import sys
import json
import datetime
import traceback
import subprocess
import webview
from pathlib import Path

from core.utils import is_admin, run_as_admin, hide_console, show_error_popup
from modules.autorun_module  import AutorunApi,  HTML as AUTORUN_HTML
from modules.network_module  import NetworkApi,  HTML as NETWORK_HTML
from modules.tasks_module    import TasksApi,    HTML as TASKS_HTML
from modules.dns_module      import DnsApi,      HTML as DNS_HTML

# ---------------------------------------------------------------------------
APP_VERSION = "2.0.0"
REPORTS_DIR = Path(os.path.abspath(sys.argv[0])).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
# ---------------------------------------------------------------------------


class HubApi:
    """API principal do Hub — gerencia abertura de módulos e relatório master."""

    def __init__(self):
        self._base_dir = Path(os.path.abspath(sys.argv[0])).parent

    # --- Info ---
    def get_status(self) -> dict:
        return {
            "is_admin": is_admin(),
            "version":  APP_VERSION,
            "computer": os.environ.get("COMPUTERNAME", "Unknown"),
            "user":     os.environ.get("USERNAME", "Unknown"),
        }

    # --- Módulos ---
    def open_autorun(self):
        webview.create_window(
            "Sentinel — Autorun", html=AUTORUN_HTML,
            js_api=AutorunApi(), width=1300, height=850,
            background_color="#030305"
        )

    def open_network(self):
        webview.create_window(
            "Sentinel — Network Pulse", html=NETWORK_HTML,
            js_api=NetworkApi(), width=1400, height=850,
            background_color="#030305"
        )

    def open_tasks(self):
        webview.create_window(
            "Sentinel — TaskGuard", html=TASKS_HTML,
            js_api=TasksApi(), width=1300, height=850,
            background_color="#030305"
        )

    def open_dns(self):
        webview.create_window(
            "Sentinel — Shield DNS", html=DNS_HTML,
            js_api=DnsApi(), width=1300, height=850,
            background_color="#030305"
        )

    # --- Relatório Master ---
    def generate_master_report(self) -> dict:
        """Orquestra todos os scanners e gera um JSON consolidado."""
        from scanners.autorun  import AutorunScanner
        from scanners.network  import NetworkScanner
        from scanners.tasks    import TasksScanner
        from scanners.dns      import DNSScanner

        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report = {
            "metadata": {
                "timestamp": ts,
                "version":   APP_VERSION,
                "computer":  os.environ.get("COMPUTERNAME", "Unknown"),
                "user":      os.environ.get("USERNAME", "Unknown"),
                "is_admin":  is_admin(),
            },
            "sections": {}
        }

        scanners = [
            ("autorun",  AutorunScanner,  "scan"),
            ("network",  NetworkScanner,  "get_connections"),
            ("tasks",    TasksScanner,    "scan"),
        ]

        for key, ScannerClass, method in scanners:
            try:
                scanner = ScannerClass()
                data = getattr(scanner, method)()
                # Remover dados binários (ícones base64) do relatório
                report["sections"][key] = [
                    {k: v for k, v in item.items() if k != "icon"}
                    for item in data
                ]
            except Exception as e:
                report["sections"][f"{key}_error"] = str(e)

        # DNS separado (retorna dicts simples)
        try:
            dns_scanner = DNSScanner()
            report["sections"]["dns"] = dns_scanner.get_dns_settings()
        except Exception as e:
            report["sections"]["dns_error"] = str(e)

        ts_file = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = REPORTS_DIR / f"MASTER_AUDIT_{ts_file}.json"
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=4, ensure_ascii=False)
            return {"success": True, "path": str(filepath)}
        except Exception as e:
            return {"success": False, "message": str(e)}


# ---------------------------------------------------------------------------
# HTML do Hub
# ---------------------------------------------------------------------------
HUB_HTML = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Sentinel Audit Suite</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #020204;
            --surf: #0a0a12;
            --surf2: #10101a;
            --accent: #00f2ff;
            --accent-dim: rgba(0, 242, 255, 0.1);
            --accent-glow: rgba(0, 242, 255, 0.25);
            --border: #1a1a28;
            --text: #e2e2ee;
            --dim: #5a5a70;
            --danger: #ff3366;
            --success: #00e87a;
            --warning: #ffaa00;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body { height: 100%; overflow: hidden; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Outfit', sans-serif;
            display: flex;
            flex-direction: column;
        }

        /* ── Hero ──────────────────────────────────────── */
        .hero {
            position: relative;
            padding: 55px 60px 45px;
            border-bottom: 1px solid var(--border);
            overflow: hidden;
            flex-shrink: 0;
        }
        .hero-grid {
            position: absolute; inset: 0;
            background-image:
                linear-gradient(var(--border) 1px, transparent 1px),
                linear-gradient(90deg, var(--border) 1px, transparent 1px);
            background-size: 40px 40px;
            opacity: 0.35;
            mask-image: radial-gradient(ellipse 80% 100% at 50% 0%, black 40%, transparent 100%);
        }
        .hero-glow {
            position: absolute; top: -120px; left: 50%;
            transform: translateX(-50%);
            width: 600px; height: 300px;
            background: radial-gradient(ellipse, rgba(0,242,255,0.12) 0%, transparent 70%);
            pointer-events: none;
        }
        .hero-content { position: relative; z-index: 1; display: flex; justify-content: space-between; align-items: flex-end; }
        .hero-left {}
        .hero-eyebrow { font-size: 10px; letter-spacing: 4px; text-transform: uppercase; color: var(--accent); font-weight: 700; margin-bottom: 12px; opacity: 0.8; }
        .hero-title {
            font-size: 44px; font-weight: 900; letter-spacing: -1px;
            line-height: 1;
            background: linear-gradient(130deg, #ffffff 30%, var(--accent) 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .hero-subtitle { font-size: 13px; color: var(--dim); margin-top: 10px; letter-spacing: 1px; }
        .hero-right { display: flex; flex-direction: column; align-items: flex-end; gap: 10px; }
        .status-pill {
            display: flex; align-items: center; gap: 8px;
            padding: 6px 14px; border-radius: 20px;
            border: 1px solid var(--border); background: var(--surf);
            font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
        }
        .status-dot { width: 7px; height: 7px; border-radius: 50%; }
        .status-dot.green { background: var(--success); box-shadow: 0 0 8px var(--success); }
        .status-dot.yellow { background: var(--warning); box-shadow: 0 0 8px var(--warning); }
        .meta-info { font-size: 11px; color: var(--dim); text-align: right; }

        /* ── Module Grid ────────────────────────────────── */
        .modules-section { flex: 1; overflow-y: auto; padding: 40px 60px; }
        .modules-section::-webkit-scrollbar { width: 5px; }
        .modules-section::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }

        .section-label { font-size: 10px; color: var(--dim); letter-spacing: 3px; text-transform: uppercase; font-weight: 700; margin-bottom: 20px; }

        .module-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; margin-bottom: 32px; }

        .module-card {
            background: var(--surf); border: 1px solid var(--border);
            border-radius: 16px; padding: 26px 28px;
            display: flex; align-items: flex-start; gap: 20px;
            cursor: pointer; transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative; overflow: hidden;
        }
        .module-card::before {
            content: '';
            position: absolute; top: 0; left: 0; right: 0; height: 1px;
            background: linear-gradient(90deg, transparent, var(--accent-glow), transparent);
            opacity: 0; transition: opacity 0.3s;
        }
        .module-card:hover { transform: translateY(-5px); border-color: rgba(0,242,255,0.35); box-shadow: 0 20px 50px rgba(0,0,0,0.6), 0 0 30px var(--accent-dim); }
        .module-card:hover::before { opacity: 1; }

        .card-icon {
            width: 52px; height: 52px; border-radius: 14px;
            display: flex; align-items: center; justify-content: center;
            font-size: 24px; flex-shrink: 0;
            background: var(--accent-dim); border: 1px solid rgba(0,242,255,0.15);
        }
        .card-body { flex: 1; }
        .card-name { font-size: 15px; font-weight: 800; letter-spacing: 0.5px; color: var(--text); margin-bottom: 6px; }
        .card-desc { font-size: 12px; color: var(--dim); line-height: 1.6; }
        .card-arrow { font-size: 16px; color: var(--dim); align-self: center; opacity: 0; transition: opacity 0.2s, transform 0.2s; }
        .module-card:hover .card-arrow { opacity: 1; transform: translateX(4px); }

        /* ── Master Report Button ───────────────────────── */
        .master-section { padding: 0 60px 40px; flex-shrink: 0; }
        .master-btn {
            width: 100%; padding: 18px;
            background: linear-gradient(135deg, rgba(0,242,255,0.08) 0%, rgba(0,242,255,0.04) 100%);
            border: 1px solid rgba(0,242,255,0.25); border-radius: 14px;
            color: var(--accent); font-weight: 800; font-size: 13px;
            letter-spacing: 3px; text-transform: uppercase;
            cursor: pointer; transition: all 0.3s; font-family: 'Outfit', sans-serif;
            display: flex; align-items: center; justify-content: center; gap: 12px;
        }
        .master-btn:hover { background: rgba(0,242,255,0.12); box-shadow: 0 0 40px var(--accent-dim); border-color: var(--accent); }
        .master-btn:disabled { opacity: 0.4; cursor: wait; }
        .master-btn .btn-spinner { width: 16px; height: 16px; border: 2px solid rgba(0,242,255,0.3); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.7s linear infinite; display: none; }
        .master-btn.loading .btn-spinner { display: block; }
        .master-btn.loading .btn-label { opacity: 0.7; }

        @keyframes spin { to { transform: rotate(360deg); } }

        /* ── Toast ──────────────────────────────────────── */
        .toast {
            position: fixed; bottom: 30px; right: 30px;
            background: var(--surf2); border: 1px solid var(--border);
            border-radius: 12px; padding: 14px 20px;
            font-size: 13px; font-weight: 600; color: var(--text);
            transform: translateY(80px); opacity: 0;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            z-index: 9999; max-width: 360px;
        }
        .toast.show { transform: translateY(0); opacity: 1; }
        .toast.success { border-color: rgba(0,232,122,0.4); }
        .toast.error   { border-color: rgba(255,51,102,0.4); }
        .toast-title { font-weight: 800; margin-bottom: 4px; }
        .toast-body { font-size: 11px; color: var(--dim); word-break: break-all; }
    </style>
</head>
<body>
    <div class="hero">
        <div class="hero-grid"></div>
        <div class="hero-glow"></div>
        <div class="hero-content">
            <div class="hero-left">
                <div class="hero-eyebrow">Sistema de Auditoria de Segurança</div>
                <div class="hero-title">SENTINEL<br>SUITE</div>
                <div class="hero-subtitle">Monitoramento e análise forense do Windows</div>
            </div>
            <div class="hero-right">
                <div class="status-pill">
                    <div class="status-dot" id="admin-dot"></div>
                    <span id="admin-label">Verificando...</span>
                </div>
                <div class="meta-info" id="meta-info">...</div>
            </div>
        </div>
    </div>

    <div class="modules-section">
        <div class="section-label">Módulos de Análise</div>
        <div class="module-grid">
            <div class="module-card" onclick="open_module('autorun')">
                <div class="card-icon">🚀</div>
                <div class="card-body">
                    <div class="card-name">Auditoria de Inicialização</div>
                    <div class="card-desc">Monitore toda entrada que inicia automaticamente com o Windows — Registro, pastas de Startup e scripts ocultos. Detecte e remova ameaças de persistência.</div>
                </div>
                <div class="card-arrow">›</div>
            </div>
            <div class="module-card" onclick="open_module('network')">
                <div class="card-icon">📡</div>
                <div class="card-body">
                    <div class="card-name">Network Pulse</div>
                    <div class="card-desc">Visualize todas as conexões TCP ativas em tempo real. Identifique processos suspeitos se comunicando com servidores externos e encerre conexões instantaneamente.</div>
                </div>
                <div class="card-arrow">›</div>
            </div>
            <div class="module-card" onclick="open_module('tasks')">
                <div class="card-icon">📅</div>
                <div class="card-body">
                    <div class="card-name">TaskGuard</div>
                    <div class="card-desc">Analise o Agendador de Tarefas do Windows. Malwares usam tarefas agendadas para persistência — aqui você pode visualizar, desativar e deletar qualquer entrada.</div>
                </div>
                <div class="card-arrow">›</div>
            </div>
            <div class="module-card" onclick="open_module('dns')">
                <div class="card-icon">🛡️</div>
                <div class="card-body">
                    <div class="card-name">Shield DNS & Hosts</div>
                    <div class="card-desc">Verifique se seus servidores DNS foram comprometidos e edite o arquivo Hosts diretamente. Aplique presets de DNS seguro (Google, Cloudflare, Quad9) com um clique.</div>
                </div>
                <div class="card-arrow">›</div>
            </div>
        </div>
    </div>

    <div class="master-section">
        <button class="master-btn" id="master-btn" onclick="generateMasterReport()">
            <div class="btn-spinner"></div>
            <span class="btn-label">⚡  Gerar Relatório Master Completo</span>
        </button>
    </div>

    <div class="toast" id="toast">
        <div class="toast-title" id="toast-title"></div>
        <div class="toast-body" id="toast-body"></div>
    </div>

    <script>
        let toastTimer = null;

        function showToast(title, body, type = '') {
            const t = document.getElementById('toast');
            document.getElementById('toast-title').textContent = title;
            document.getElementById('toast-body').textContent  = body;
            t.className = 'toast show ' + type;
            clearTimeout(toastTimer);
            toastTimer = setTimeout(() => t.className = 'toast', 4000);
        }

        async function init() {
            const status = await pywebview.api.get_status();
            const dot   = document.getElementById('admin-dot');
            const label = document.getElementById('admin-label');
            if (status.is_admin) {
                dot.className = 'status-dot green';
                label.textContent = 'Modo Administrador';
                label.style.color = 'var(--success)';
            } else {
                dot.className = 'status-dot yellow';
                label.textContent = 'Sem Privilégios Admin';
                label.style.color = 'var(--warning)';
            }
            document.getElementById('meta-info').innerHTML =
                `${status.computer} — v${status.version}`;
        }

        async function open_module(name) {
            const methods = {
                autorun: 'open_autorun',
                network: 'open_network',
                tasks:   'open_tasks',
                dns:     'open_dns',
            };
            await pywebview.api[methods[name]]();
        }

        async function generateMasterReport() {
            const btn = document.getElementById('master-btn');
            btn.disabled = true;
            btn.classList.add('loading');
            const res = await pywebview.api.generate_master_report();
            btn.disabled = false;
            btn.classList.remove('loading');
            if (res.success) {
                showToast('✅ Relatório Gerado', res.path, 'success');
            } else {
                showToast('❌ Erro na Geração', res.message, 'error');
            }
        }

        window.addEventListener('pywebviewready', init);
    </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        run_as_admin()
        hide_console()
        api = HubApi()
        webview.create_window(
            "Sentinel Audit Suite",
            html=HUB_HTML,
            js_api=api,
            width=1100, height=780,
            background_color="#020204",
            min_size=(900, 650)
        )
        webview.start(icon='icon.png')
    except Exception:
        show_error_popup(traceback.format_exc(), "Sentinel — Erro Crítico")
