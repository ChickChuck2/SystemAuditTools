# Sentinel Audit Suite

> Sistema profissional de auditoria e monitoramento de segurança para Windows — com interface GUI baseada em `pywebview`.

---

## 📦 Estrutura do Projeto

```
SystemAuditTools/
│
├── build.py                 # Builder PyInstaller → gera .exe
├── requirements.txt         # Dependências do projeto
├── icon.png                 # Ícone da aplicação (janela)
├── icon.ico                 # Ícone do executável (Windows)
├── sentinel.css             # (legado — mantido para referência)
│
├── core/                    # Componentes compartilhados
│   ├── utils.py             # is_admin, run_as_admin, hide_console, resolve_path
│   └── icons.py             # Extração de ícones via Windows Shell API
│
├── scanners/                # Lógica de negócio (sem GUI)
│   ├── autorun.py           # Scanner de entradas de Startup
│   ├── network.py           # Monitor de conexões TCP
│   ├── tasks.py             # Auditor de Tarefas Agendadas
│   └── dns.py               # Scanner de DNS e Hosts
│
├── modules/                 # Módulos GUI (pywebview)
│   ├── autorun_module.py    # API + HTML — Auditoria de Inicialização
│   ├── network_module.py    # API + HTML — Network Pulse
│   ├── tasks_module.py      # API + HTML — TaskGuard
│   └── dns_module.py        # API + HTML — Shield DNS & Hosts
│
├── reports/                 # Relatórios gerados (auto-criado)
├── build/                   # Artefatos de build (gitignored)
└── dist/                    # Executável final (gitignored)
```

---

## 🚀 Instalação

### Pré-requisitos

- Python 3.10+
- Windows 10/11
- Privilégios de Administrador (para funcionalidades completas)

### Instalar dependências

```bash
pip install -r requirements.txt
```

---

## ▶️ Uso

### Rodar o aplicativo

```bash
python main.py
```

> O app solicita elevação UAC automaticamente se não for Administrador.

### Módulos disponíveis

| Módulo | Descrição |
|--------|-----------|
| 🚀 **Auditoria de Inicialização** | Escaneia Registro (HKCU/HKLM Run) e pastas de Startup. Detecta e remove entradas suspeitas. |
| 📡 **Network Pulse** | Monitor em tempo real de conexões TCP. Mostra processo, PID, endereços local/remoto e estado. Auto-refresh a cada 5s. |
| 📅 **TaskGuard** | Lista todas as tarefas agendadas do Windows. Permite ativar, desativar e deletar tarefas. |
| 🛡️ **Shield DNS & Hosts** | Exibe servidores DNS por interface. Editor direto do arquivo `hosts`. Presets rápidos (Google, Cloudflare, Quad9). |

### Relatório Master

Clique em **"⚡ Gerar Relatório Master Completo"** no Hub para criar um JSON consolidado com dados de todos os módulos em `reports/MASTER_AUDIT_<timestamp>.json`.

---

## 📦 Build (Gerar Executável)

```bash
python build.py
```

Gera `dist/Sentinel_Audit.exe` — um único executável portátil, sem necessidade de Python instalado.

---

---

## 🔒 Segurança

- A chave mestra de acesso remoto (`master_key.txt`) é gerada automaticamente com 64 caracteres hexadecimais (256-bit entropy).
- **Nunca commite** o arquivo `master_key.txt` no Git — ele está no `.gitignore`.
- O servidor de acesso remoto deve ser usado apenas em redes confiáveis ou com VPN.

---

## 📋 Dependências

| `pywebview` | 6.1 | Interface GUI via WebView2 |
| `Pillow` | 12.0.0 | Manipulação e conversão de ícones |
| `pyinstaller` | 6.18.x | Compilação do executável |
| `colorama` | 0.4.6 | Saída colorida no builder |

> Todas as funcionalidades de auditoria usam apenas a stdlib do Python + WinAPI via `ctypes`.
