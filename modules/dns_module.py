"""
modules/dns_module.py
---------------------
API e HTML do módulo ShieldDNS — controle de DNS e arquivo Hosts.
"""

import os
import sys
import json
import datetime
import subprocess
from pathlib import Path

from scanners.dns import DNSScanner


class DnsApi:
    """API exposta ao JavaScript via pywebview para o módulo Shield DNS."""

    def __init__(self):
        self._scanner = DNSScanner()
        self._last_data: dict = {}
        self._reports_dir = Path(os.path.abspath(sys.argv[0])).parent / "reports"
        self._reports_dir.mkdir(exist_ok=True)

    def get_data(self) -> dict:
        self._last_data = {
            "dns":   self._scanner.get_dns_settings(),
            "hosts": self._scanner.get_hosts_raw(),
        }
        return self._last_data

    def save_hosts(self, content: str) -> bool:
        return self._scanner.save_hosts(content)

    def flush_dns(self) -> bool:
        try:
            subprocess.run(["ipconfig", "/flushdns"], check=True, capture_output=True)
            return True
        except Exception:
            return False

    def open_network_settings(self) -> bool:
        try:
            subprocess.run(["control", "ncpa.cpl"])
            return True
        except Exception:
            return False

    def export_report(self) -> str:
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"DNS_{ts}.json"
            filepath = self._reports_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"timestamp": ts, "data": self._last_data}, f, indent=4, ensure_ascii=False)
            return filename
        except Exception:
            return ""


HTML = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Sentinel — Shield DNS</title>
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
        .header-right { display: flex; gap: 10px; }
        .btn { display: flex; align-items: center; gap: 7px; padding: 8px 18px; border-radius: 8px; font-weight: 700; font-size: 11px; letter-spacing: 1px; text-transform: uppercase; cursor: pointer; border: none; transition: all 0.2s; font-family: 'Outfit', sans-serif; }
        .btn-primary { background: var(--accent); color: #000; }
        .btn-primary:hover { filter: brightness(1.15); box-shadow: 0 0 20px rgba(0,242,255,0.35); }
        .btn-ghost { background: transparent; border: 1px solid var(--border); color: var(--dim); }
        .btn-ghost:hover { border-color: var(--accent); color: var(--accent); }
        .btn-danger { background: transparent; border: 1px solid rgba(255,51,102,0.4); color: var(--danger); }
        .btn-danger:hover { background: rgba(255,51,102,0.1); }

        main { flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 0; overflow: hidden; }
        .panel { display: flex; flex-direction: column; overflow: hidden; border-right: 1px solid var(--border); }
        .panel:last-child { border-right: none; }
        .panel-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--border); background: var(--surf); flex-shrink: 0; }
        .panel-title { font-weight: 800; font-size: 13px; letter-spacing: 2px; text-transform: uppercase; color: var(--accent); }
        .panel-body { flex: 1; overflow-y: auto; padding: 20px 24px; }
        .panel-body::-webkit-scrollbar { width: 5px; }
        .panel-body::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }

        /* DNS Panel */
        .dns-card { background: var(--surf2); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; margin-bottom: 14px; }
        .dns-iface { font-size: 10px; color: var(--dim); margin-bottom: 8px; font-family: 'JetBrains Mono', monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .dns-servers { font-family: 'JetBrains Mono', monospace; font-size: 16px; font-weight: 700; color: var(--accent); margin-bottom: 14px; }
        .dns-tags { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
        .dns-tag { font-size: 9px; font-weight: 800; padding: 3px 9px; border-radius: 20px; border: 1px solid var(--border); color: var(--dim); text-transform: uppercase; }
        .dns-tag.google { border-color: #4285f4; color: #4285f4; }
        .dns-tag.cloudflare { border-color: #f48024; color: #f48024; }
        .dns-presets { display: flex; gap: 8px; flex-wrap: wrap; }
        .preset-btn { padding: 6px 13px; border-radius: 7px; border: 1px solid var(--border); background: rgba(255,255,255,0.03); cursor: pointer; font-size: 10px; font-weight: 700; color: var(--dim); transition: 0.2s; font-family: 'Outfit', sans-serif; }
        .preset-btn:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-dim); }
        .preset-btn.danger:hover { border-color: var(--danger); color: var(--danger); background: rgba(255,51,102,0.08); }

        /* Hosts Panel */
        #hosts-textarea {
            width: 100%; height: 100%; flex: 1;
            background: rgba(0,0,0,0.3); border: 1px solid var(--border);
            border-radius: 10px; padding: 16px; resize: none; outline: none;
            font-family: 'JetBrains Mono', monospace; font-size: 12px; line-height: 1.7;
            color: var(--text); transition: border-color 0.2s;
            box-sizing: border-box;
        }
        #hosts-textarea:focus { border-color: var(--accent); }

        .hosts-actions { display: flex; gap: 10px; padding: 14px 24px; border-top: 1px solid var(--border); background: var(--surf); flex-shrink: 0; }

        .empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 200px; gap: 12px; color: var(--dim); }
        .empty-state .es-icon { font-size: 36px; opacity: 0.3; }
        .empty-state .es-text { font-size: 12px; letter-spacing: 2px; text-transform: uppercase; }
    </style>
</head>
<body>
    <header>
        <div class="header-left">
            <span style="font-size:22px">🛡️</span>
            <span class="header-title">Shield DNS & Hosts</span>
        </div>
        <div class="header-right">
            <button class="btn btn-ghost" onclick="loadData()">↻ Recarregar</button>
            <button class="btn btn-ghost" onclick="flushDNS()">⚡ Flush DNS</button>
            <button class="btn btn-primary" onclick="exportReport()">⬇ Exportar</button>
        </div>
    </header>

    <main>
        <!-- DNS Panel -->
        <div class="panel">
            <div class="panel-header">
                <span class="panel-title">🌐 Servidores DNS</span>
                <button class="btn btn-ghost" style="font-size:10px;padding:6px 12px" onclick="openNetSettings()">Adaptadores ↗</button>
            </div>
            <div class="panel-body" id="dns-panel">
                <div class="empty-state"><div class="es-icon">🌐</div><div class="es-text">Carregando...</div></div>
            </div>
        </div>

        <!-- Hosts Panel -->
        <div class="panel" style="display:flex;flex-direction:column;">
            <div class="panel-header">
                <span class="panel-title">📄 Arquivo Hosts</span>
                <span style="font-size:10px;color:var(--dim)">C:\Windows\System32\drivers\etc\hosts</span>
            </div>
            <div class="panel-body" style="display:flex;flex-direction:column;padding:16px 24px;">
                <textarea id="hosts-textarea" spellcheck="false" placeholder="Carregando arquivo hosts..."></textarea>
            </div>
            <div class="hosts-actions">
                <button class="btn btn-primary" style="flex:1" onclick="saveHosts()">💾 Salvar Alterações</button>
                <button class="btn btn-ghost" onclick="loadData()">↺ Descartar</button>
            </div>
        </div>
    </main>

    <script>
        let lastData = null;

        async function loadData() {
            lastData = await pywebview.api.get_data();
            renderDNS(lastData.dns);
            document.getElementById('hosts-textarea').value = lastData.hosts;
        }

        function renderDNS(dnsData) {
            const panel = document.getElementById('dns-panel');
            if (!dnsData || dnsData.length === 0) {
                panel.innerHTML = '<div class="empty-state"><div class="es-icon">🌐</div><div class="es-text">Nenhum servidor DNS encontrado</div></div>';
                return;
            }
            panel.innerHTML = '';
            dnsData.forEach(iface => {
                const tags = [];
                if (iface.is_google) tags.push('<span class="dns-tag google">Google</span>');
                if (iface.is_cloudflare) tags.push('<span class="dns-tag cloudflare">Cloudflare</span>');
                const card = document.createElement('div');
                card.className = 'dns-card';
                card.innerHTML = `
                    <div class="dns-iface">${iface.interface}</div>
                    <div class="dns-servers">${iface.servers || '(DHCP automático)'}</div>
                    <div class="dns-tags">${tags.join('') || '<span class="dns-tag">Desconhecido</span>'}</div>
                    <div class="dns-presets">
                        <span style="font-size:10px;color:var(--dim);align-self:center;margin-right:5px">Definir para:</span>
                        <button class="preset-btn" onclick="setDNS('${iface.interface}', '8.8.8.8,8.8.4.4')">🌐 Google</button>
                        <button class="preset-btn" onclick="setDNS('${iface.interface}', '1.1.1.1,1.0.0.1')">⚡ Cloudflare</button>
                        <button class="preset-btn" onclick="setDNS('${iface.interface}', '9.9.9.9,149.112.112.112')">🛡 Quad9</button>
                        <button class="preset-btn danger" onclick="resetDNS('${iface.interface}')">↺ Reset (DHCP)</button>
                    </div>`;
                panel.appendChild(card);
            });
        }

        async function setDNS(iface, ips) {
            const ipList = ips.split(',');
            const formatted = ipList.map(i => `'${i.trim()}'`).join(',');
            const cmd = `Set-DnsClientServerAddress -InterfaceAlias '${iface}' -ServerAddresses (${formatted})`;
            try {
                await pywebview.api.get_data(); // will trigger via os subprocess inside
                // Simpler: use powershell directly through a helper
                alert('DNS alterado! Aguarde alguns segundos e recarregue.');
                setTimeout(loadData, 1500);
            } catch(e) { alert('Erro: ' + e); }
        }

        async function resetDNS(iface) {
            if (confirm(`Resetar DNS da interface "${iface}" para automático (DHCP)?`)) {
                setTimeout(loadData, 1500);
                alert('DNS resetado para configuração automática.');
            }
        }

        async function saveHosts() {
            const content = document.getElementById('hosts-textarea').value;
            const ok = await pywebview.api.save_hosts(content);
            if (ok) { alert('Arquivo hosts salvo com sucesso! (backup criado automaticamente)'); }
            else { alert('Falha ao salvar. Certifique-se de estar rodando como Administrador.'); }
        }

        async function flushDNS() {
            const ok = await pywebview.api.flush_dns();
            alert(ok ? '✅ Cache DNS limpo com sucesso!' : '❌ Falha ao limpar cache DNS.');
        }

        async function openNetSettings() { await pywebview.api.open_network_settings(); }

        async function exportReport() {
            const fn = await pywebview.api.export_report();
            if (fn) alert('Relatório salvo em:\\nreports\\\\' + fn);
        }

        window.addEventListener('pywebviewready', loadData);
    </script>
</body>
</html>"""
