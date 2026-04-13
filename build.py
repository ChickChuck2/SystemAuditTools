"""
build.py
--------
Builder do Sentinel Audit Suite — gera executável Windows via PyInstaller.

Uso:
    python build.py

Saída: dist/Sentinel_Audit.exe
"""

import os
import re
import sys
import io
import time
import shutil
import subprocess
from datetime import datetime

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class _Dummy:
        def __getattr__(self, _): return ""
    Fore = Style = _Dummy()

# ─── Configuração ─────────────────────────────────────────────────────────────
APP_NAME       = "Sentinel_Audit"
VERSION        = "2.0.0"
SOURCE_SCRIPT  = "main.py"
EXTRA_DATA     = [
    ("sentinel.css", "."),
    ("icon.png", "."),
]
# ──────────────────────────────────────────────────────────────────────────────


def check_dependencies():
    required = {"pyinstaller": "pyinstaller", "colorama": "colorama", "pywebview": "webview"}
    print(f"{Fore.CYAN}[*] Verificando dependências...")
    for lib, import_name in required.items():
        try:
            if lib == "pyinstaller":
                subprocess.check_output(["pyinstaller", "--version"], stderr=subprocess.STDOUT)
            else:
                __import__(import_name)
            print(f"{Fore.GREEN}  ✓ {lib}")
        except Exception:
            print(f"{Fore.YELLOW}  ! Instalando {lib}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])


def print_banner():
    print(f"""
{Fore.CYAN}{Style.BRIGHT}╔══════════════════════════════════════════════════╗
{Fore.CYAN}{Style.BRIGHT}║   {Fore.WHITE}SENTINEL AUDIT SUITE — BUILDER v{VERSION}{Fore.CYAN}   ║
{Fore.CYAN}{Style.BRIGHT}╚══════════════════════════════════════════════════╝{Style.RESET_ALL}
""")


def render_progress(percent: int, stage: str = ""):
    width = 35
    filled = int(width * percent / 100)
    bar = f"{Fore.CYAN}{'█' * filled}{Fore.BLACK}{Style.BRIGHT}{'░' * (width - filled)}"
    sys.stdout.write(f"\r  {bar}{Style.RESET_ALL}  {Fore.YELLOW}{percent:3d}%{Style.RESET_ALL}  {stage:<28}")
    sys.stdout.flush()


def build():
    # Garantir que a saída do console suporte caracteres Unicode
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    check_dependencies()
    print_banner()
    start = time.time()

    # Limpar builds anteriores
    print(f"{Fore.BLUE}[*] Limpando ambiente...")
    for folder in ("build", "dist"):
        if os.path.exists(folder):
            shutil.rmtree(folder)

    # Montar comando
    add_data = []
    for src, dest in EXTRA_DATA:
        if os.path.exists(src):
            add_data += [f"--add-data={src};{dest}"]

    excludes = [
        "tkinter", "tcl", "tk", "unittest", "pydoc",
        "pydoc_data", "multiprocessing",
        "sqlite3", "test"
    ]

    cmd = [
        sys.executable, "-O", "-m", "PyInstaller",
        f"--name={APP_NAME}",
        "--onefile",
        "--windowed",
        "--noconsole",
        "--noconfirm",
        "--clean",
        "--icon=icon.ico",
        *[f"--exclude-module={m}" for m in excludes],
        *add_data,
        SOURCE_SCRIPT,
    ]

    # Stages de progresso com base no output do PyInstaller
    stages = [
        (r"Analysis",         15, "Analisando dependências"),
        (r"Collecting",       35, "Coletando módulos"),
        (r"Building PKG",     55, "Empacotando recursos"),
        (r"Appended archive", 75, "Mesclando arquivo"),
        (r"Building EXE",     90, "Finalizando binário"),
        (r"successfully",    100, "Concluído!"),
    ]

    print(f"{Fore.BLUE}[*] Iniciando compilação...\n")
    current_pct = 0
    stage_idx = 0
    full_log: list[str] = []

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="ignore"
    )

    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            full_log.append(line.strip())
            if stage_idx < len(stages):
                pattern, target, label = stages[stage_idx]
                if re.search(pattern, line, re.IGNORECASE):
                    while current_pct < target:
                        current_pct += 1
                        render_progress(current_pct, label)
                        time.sleep(0.008)
                    stage_idx += 1

    process.wait()

    print()  # quebra de linha após progress bar
    elapsed = time.time() - start

    if process.returncode == 0:
        dist_path = os.path.join("dist", f"{APP_NAME}.exe")
        size_mb = os.path.getsize(dist_path) / (1024 * 1024) if os.path.exists(dist_path) else 0
        print(f"""
{Fore.GREEN}{Style.BRIGHT}  ╔═══════════════════════════════════════════╗
  ║       BUILD CONCLUÍDO COM SUCESSO         ║
  ╚═══════════════════════════════════════════╝{Style.RESET_ALL}

  {Fore.WHITE}Executável : {Fore.YELLOW}{dist_path}
  {Fore.WHITE}Tamanho    : {Fore.CYAN}{size_mb:.2f} MB
  {Fore.WHITE}Tempo      : {Fore.CYAN}{elapsed:.1f}s
  {Fore.WHITE}Gerado em  : {Fore.CYAN}{datetime.now().strftime('%H:%M:%S')}
""")
    else:
        print(f"\n{Fore.RED}  [✗] FALHA NA COMPILAÇÃO\n")
        print(f"  {Fore.YELLOW}Últimas linhas de log:")
        for err_line in full_log[-15:]:
            print(f"    {Fore.RED}> {Fore.WHITE}{err_line}")

    input(f"\n{Style.DIM}  Pressione Enter para sair...{Style.RESET_ALL}")


if __name__ == "__main__":
    build()
