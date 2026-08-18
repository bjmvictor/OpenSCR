import json
import os
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path


APP_NAME = "OpenSCR"


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parents[1]

    return base_path / relative_path


def get_external_config_path():
    executable = Path(sys.executable).resolve()

    data_dir = executable.with_name(
        f"{executable.stem}.data"
    )

    return data_dir / "config.json"


def load_config(config_path=None):
    if config_path:
        path = Path(config_path).resolve()

    elif getattr(sys, "frozen", False):
        path = get_external_config_path()

    else:
        path = resource_path("config.json")

    if not path.exists():
        raise FileNotFoundError(
            f"Configuração do OpenSCR não encontrada:\n{path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    base_dir = path.parent

    resolved_images = []

    for image in config.get(
        "images",
        [],
    ):
        image_path = Path(image)

        if not image_path.is_absolute():
            image_path = (
                base_dir
                / image_path
            )

        resolved_images.append(
            str(image_path.resolve())
        )

    config["images"] = resolved_images

    return config


def parse_arguments():
    args = sys.argv[1:]

    mode = "/s"
    config_path = None
    self_test = False

    index = 0

    while index < len(args):
        arg = args[index]
        lowered = arg.lower()

        if lowered == "--openscr-self-test":
            self_test = True

        elif lowered == "--config":
            if index + 1 < len(args):
                config_path = args[index + 1]
                index += 1

        elif lowered.startswith("/c"):
            mode = "/c"

        elif lowered.startswith("/p"):
            mode = "/p"

        elif lowered.startswith("/s"):
            mode = "/s"

        index += 1

    return mode, config_path, self_test


def validate_config(config):
    from PySide6.QtGui import QPixmap

    images = config.get(
        "images",
        [],
    )

    if not images:
        raise RuntimeError(
            "Nenhuma imagem foi configurada."
        )

    for image in images:
        path = Path(image)

        if not path.exists():
            raise FileNotFoundError(
                f"Imagem não encontrada: {path}"
            )

        pixmap = QPixmap(
            str(path)
        )

        if pixmap.isNull():
            raise RuntimeError(
                f"Não foi possível carregar a imagem: {path}"
            )


def run_screensaver(config):
    from PySide6.QtWidgets import QApplication
    from runtime.screensaver import ScreenSaverWindow

    app = QApplication.instance()

    windows = []

    for screen in app.screens():
        window = ScreenSaverWindow(
            config,
            screen,
        )

        window.show()

        windows.append(
            window
        )

    return windows


def write_error_log():
    base = Path(
        os.environ.get(
            "LOCALAPPDATA",
            tempfile.gettempdir(),
        )
    )

    log_dir = (
        base
        / APP_NAME
        / "logs"
    )

    log_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_file = (
        log_dir
        / "screensaver.log"
    )

    with log_file.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            "\n\n"
            "====================================\n"
        )

        file.write(
            datetime.now().strftime(
                "%d/%m/%Y %H:%M:%S"
            )
        )

        file.write("\n")

        file.write(
            traceback.format_exc()
        )

    return log_file


def main():
    from PySide6.QtWidgets import (
        QApplication,
        QMessageBox,
    )

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        APP_NAME
    )

    mode, config_path, self_test = (
        parse_arguments()
    )

    config = None

    if self_test:
        config = load_config(
            config_path
        )

        validate_config(
            config
        )

        return 0

    if mode == "/c":
        QMessageBox.information(
            None,
            "OpenSCR",
            (
                "Este protetor de tela foi criado "
                "com o OpenSCR.\n\n"
                "Utilize o OpenSCR para editar "
                "ou gerar uma nova versão."
            ),
        )

        return 0

    if mode == "/p":
        # O preview nativo do painel do Windows
        # será implementado posteriormente.
        return 0

    config = load_config(
        config_path
    )

    windows = run_screensaver(
        config
    )

    # Mantém referências enquanto QApplication estiver ativo.
    app._openscr_windows = windows

    return app.exec()


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )

    except SystemExit:
        raise

    except Exception:
        log_file = write_error_log()

        traceback.print_exc()

        print()
        print(
            "OpenSCR Runtime falhou."
        )

        print(
            f"Log: {log_file}"
        )

        raise SystemExit(1)