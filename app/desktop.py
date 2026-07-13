"""Launcher desktop do Nexor Simulador empacotado para Windows.

Inicia o FastAPI em localhost, abre o navegador e mantém uma pequena janela de
controle para reabrir ou encerrar o servidor. Dados e logs ficam em
%LOCALAPPDATA%/NexorSimulador, fora da pasta do executável/instalador.
"""
from __future__ import annotations

import asyncio
import logging
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


APP_NAME = "Nexor Simulador Tributário"
APP_VERSION = "0.1.0"
HOST = "127.0.0.1"
PORTS = range(8000, 8011)


def _resource_root() -> Path:
    """Diretório dos recursos no código-fonte ou bundle PyInstaller."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root)
    return Path(__file__).resolve().parents[1]


def _local_app_data() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    return Path(base) if base else Path.home() / "AppData" / "Local"


def _configure_environment() -> tuple[Path, Path]:
    data_root = _local_app_data() / "NexorSimulador"
    database_dir = data_root / "data"
    log_dir = data_root / "logs"
    database_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    database_path = database_dir / "nexor_sim.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    os.environ["DEBUG"] = "false"
    os.environ.setdefault("SQL_ECHO", "false")

    # Os templates e estáticos usam caminhos relativos no módulo standalone.
    os.chdir(_resource_root())
    return database_path, log_dir / "nexor_simulador.log"


def _configure_logging(log_path: Path) -> None:
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        encoding="utf-8",
    )
    logging.info("Iniciando %s %s", APP_NAME, APP_VERSION)


def _is_nexor_running(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://{HOST}:{port}/empresas", timeout=0.5) as response:
            content = response.read(8192).decode("utf-8", errors="ignore")
            return response.status == 200 and "Nexor" in content
    except (OSError, urllib.error.URLError):
        return False


def _find_existing_instance() -> int | None:
    return next((port for port in PORTS if _is_nexor_running(port)), None)


def _find_free_port() -> int:
    for port in PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((HOST, port))
            except OSError:
                continue
            return port
    raise RuntimeError("Nenhuma porta livre foi encontrada entre 8000 e 8010.")


def _show_error(message: str) -> None:
    try:
        import tkinter.messagebox as messagebox

        messagebox.showerror(APP_NAME, message)
    except Exception:
        logging.exception("Não foi possível exibir a mensagem de erro")


def _open_existing(port: int) -> None:
    webbrowser.open(f"http://{HOST}:{port}/", new=2)


def _run_desktop() -> int:
    database_path, log_path = _configure_environment()
    _configure_logging(log_path)

    existing_port = _find_existing_instance()
    if existing_port is not None:
        _open_existing(existing_port)
        return 0

    # Importar somente depois de configurar DATABASE_URL e o diretório de recursos.
    import tkinter as tk
    from tkinter import messagebox

    import uvicorn

    from app.main import app
    from app.seeds import init_models, seed_all

    asyncio.run(init_models())
    asyncio.run(seed_all())

    port = _find_free_port()
    url = f"http://{HOST}:{port}/"
    config = uvicorn.Config(
        app,
        host=HOST,
        port=port,
        log_level="info",
        access_log=False,
        # Executáveis windowed não possuem sys.stdout/sys.stderr. O formatter
        # padrão do Uvicorn consulta isatty() e falha nesse cenário; usamos o
        # log em arquivo configurado acima.
        log_config=None,
        loop="asyncio",
        http="h11",
        ws="none",
        lifespan="on",
    )
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, name="nexor-server", daemon=True)

    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry("460x235")
    root.resizable(False, False)
    root.configure(bg="#f8fafc")

    title = tk.Label(
        root,
        text="Nexor Fiscal",
        font=("Segoe UI", 19, "bold"),
        fg="#0f172a",
        bg="#f8fafc",
    )
    title.pack(pady=(24, 0))
    subtitle = tk.Label(
        root,
        text="Simulador Tributário",
        font=("Segoe UI", 11),
        fg="#475569",
        bg="#f8fafc",
    )
    subtitle.pack(pady=(0, 16))

    status_var = tk.StringVar(value="Iniciando o sistema…")
    status = tk.Label(
        root,
        textvariable=status_var,
        font=("Segoe UI", 10),
        fg="#334155",
        bg="#f8fafc",
    )
    status.pack()

    button_frame = tk.Frame(root, bg="#f8fafc")
    button_frame.pack(pady=20)

    open_button = tk.Button(
        button_frame,
        text="Abrir no navegador",
        command=lambda: webbrowser.open(url, new=2),
        state=tk.DISABLED,
        width=20,
        font=("Segoe UI", 10, "bold"),
        bg="#0f172a",
        fg="white",
        activebackground="#334155",
        activeforeground="white",
        relief=tk.FLAT,
        padx=8,
        pady=8,
    )
    open_button.grid(row=0, column=0, padx=6)

    stopping = False

    def finish_shutdown() -> None:
        if server_thread.is_alive():
            root.after(150, finish_shutdown)
            return
        root.destroy()

    def stop_application() -> None:
        nonlocal stopping
        if stopping:
            return
        stopping = True
        status_var.set("Encerrando…")
        open_button.configure(state=tk.DISABLED)
        close_button.configure(state=tk.DISABLED)
        server.should_exit = True
        root.after(150, finish_shutdown)

    close_button = tk.Button(
        button_frame,
        text="Encerrar",
        command=stop_application,
        width=12,
        font=("Segoe UI", 10),
        bg="#e2e8f0",
        fg="#0f172a",
        activebackground="#cbd5e1",
        relief=tk.FLAT,
        padx=8,
        pady=8,
    )
    close_button.grid(row=0, column=1, padx=6)

    def wait_until_ready() -> None:
        for _ in range(60):
            if _is_nexor_running(port):
                root.after(0, mark_ready)
                return
            if not server_thread.is_alive():
                break
            time.sleep(0.25)
        root.after(0, mark_failed)

    def mark_ready() -> None:
        status_var.set(f"Sistema em execução: {url}")
        open_button.configure(state=tk.NORMAL)
        webbrowser.open(url, new=2)

    def mark_failed() -> None:
        status_var.set("Não foi possível iniciar o sistema.")
        messagebox.showerror(
            APP_NAME,
            f"Não foi possível iniciar o simulador.\n\nConsulte o log em:\n{log_path}",
        )

    root.protocol("WM_DELETE_WINDOW", stop_application)
    server_thread.start()
    threading.Thread(target=wait_until_ready, name="nexor-browser", daemon=True).start()

    logging.info("Banco: %s", database_path)
    logging.info("Servidor: %s", url)
    root.mainloop()
    return 0


def main() -> int:
    try:
        return _run_desktop()
    except Exception as exc:
        logging.exception("Falha fatal no launcher desktop")
        _show_error(
            "O Nexor Simulador não conseguiu iniciar.\n\n"
            f"Detalhe: {exc}\n\n"
            "Envie esta mensagem ao suporte responsável."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
