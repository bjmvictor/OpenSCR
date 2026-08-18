
import os
import shutil
import subprocess
import sys
from pathlib import Path


# ============================================================
# OpenSCR Build Configuration
# ============================================================

APP_NAME = "OpenSCR"
APP_VERSION = "0.1.0-alpha"


ROOT_DIR = Path(
    __file__
).resolve().parent


CREATOR_FILE = (
    ROOT_DIR
    / "creator.py"
)


ASSETS_DIR = (
    ROOT_DIR
    / "assets"
)


ICON_FILE = (
    ASSETS_DIR
    / "OpenSCR.ico"
)


RESOURCES_DIR = (
    ROOT_DIR
    / "resources"
)


RUNTIME_EXE = (
    RESOURCES_DIR
    / "OpenSCRRuntime.exe"
)


RUNTIME_SCR = (
    RESOURCES_DIR
    / "OpenSCRRuntime.scr"
)


BUILD_DIR = (
    ROOT_DIR
    / "build"
    / "openscr"
)


DIST_DIR = (
    ROOT_DIR
    / "dist"
)


RELEASE_DIR = (
    ROOT_DIR
    / "release"
)


# ============================================================
# Helpers
# ============================================================

def print_header():
    print()
    print("=" * 60)
    print(f" OpenSCR {APP_VERSION}")
    print(" Portable Build")
    print("=" * 60)
    print()


def validate_files():
    required_files = [
        CREATOR_FILE,
        RUNTIME_EXE,
        RUNTIME_SCR,
    ]

    missing = [
        path
        for path in required_files
        if not path.exists()
    ]

    if missing:
        print(
            "Arquivos necessários não encontrados:"
        )

        print()

        for path in missing:
            print(
                f"  - {path}"
            )

        print()
        print(
            "Se o runtime estiver faltando, execute:"
        )

        print()
        print(
            "  python build_runtime.py"
        )

        raise SystemExit(1)


def clean_previous_build():
    if BUILD_DIR.exists():
        print(
            "Removendo build anterior..."
        )

        shutil.rmtree(
            BUILD_DIR,
            ignore_errors=True,
        )

    BUILD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    DIST_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RELEASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def add_data_argument(
    command,
    source,
    destination,
):
    separator = (
        ";"
        if os.name == "nt"
        else ":"
    )

    command.extend(
        [
            "--add-data",
            (
                f"{source}"
                f"{separator}"
                f"{destination}"
            ),
        ]
    )


# ============================================================
# Build
# ============================================================

def build():
    print_header()

    validate_files()
    clean_previous_build()

    print(
        "Compilando OpenSCR..."
    )

    print()

    command = [
        sys.executable,
        "-m",
        "PyInstaller",

        "--noconfirm",
        "--clean",

        # Aplicação portátil em um único EXE.
        "--onefile",

        # Não abrir console ao iniciar.
        "--windowed",

        # Evita compressão UPX.
        "--noupx",

        # Nome do executável.
        "--name",
        APP_NAME,

        # Diretórios de saída.
        "--distpath",
        str(DIST_DIR),

        "--workpath",
        str(BUILD_DIR),

        "--specpath",
        str(BUILD_DIR),

        # Garante que módulos locais possam ser localizados.
        "--paths",
        str(ROOT_DIR),
    ]

    # --------------------------------------------------------
    # Ícone
    # --------------------------------------------------------

    if ICON_FILE.exists():
        command.extend(
            [
                "--icon",
                str(ICON_FILE),
            ]
        )

        print(
            f"Ícone: {ICON_FILE}"
        )

    else:
        print(
            "Aviso: assets/OpenSCR.ico "
            "não encontrado."
        )

        print(
            "O executável será gerado "
            "com o ícone padrão."
        )

    # --------------------------------------------------------
    # Runtime
    # --------------------------------------------------------

    add_data_argument(
        command,
        RUNTIME_EXE,
        "resources",
    )

    add_data_argument(
        command,
        RUNTIME_SCR,
        "resources",
    )

    # --------------------------------------------------------
    # Assets
    # --------------------------------------------------------

    if ASSETS_DIR.exists():
        add_data_argument(
            command,
            ASSETS_DIR,
            "assets",
        )

    # --------------------------------------------------------
    # Entrypoint
    # --------------------------------------------------------

    command.append(
        str(CREATOR_FILE)
    )

    print()
    print(
        "Executando PyInstaller..."
    )

    print()

    result = subprocess.run(
        command,
        cwd=str(ROOT_DIR),
    )

    if result.returncode != 0:
        raise RuntimeError(
            (
                "O PyInstaller terminou "
                "com erro."
            )
        )

    # ========================================================
    # Validate output
    # ========================================================

    generated_exe = (
        DIST_DIR
        / f"{APP_NAME}.exe"
    )

    if not generated_exe.exists():
        raise RuntimeError(
            (
                "O processo terminou sem erro, "
                "mas OpenSCR.exe não foi encontrado."
            )
        )

    # ========================================================
    # Portable release
    # ========================================================

    portable_name = (
        f"{APP_NAME}-"
        f"{APP_VERSION}-Portable.exe"
    )

    portable_file = (
        RELEASE_DIR
        / portable_name
    )

    if portable_file.exists():
        portable_file.unlink()

    shutil.copy2(
        generated_exe,
        portable_file,
    )

    # ========================================================
    # Result
    # ========================================================

    size_mb = (
        portable_file.stat().st_size
        / 1024
        / 1024
    )

    print()
    print("=" * 60)
    print(" BUILD CONCLUÍDO")
    print("=" * 60)

    print()
    print(
        f"Arquivo: {portable_file}"
    )

    print(
        f"Tamanho: {size_mb:.2f} MB"
    )

    print()
    print(
        "A versão portátil não requer "
        "Python instalado no computador."
    )

    print()


# ============================================================
# Main
# ============================================================

def main():
    try:
        build()

    except KeyboardInterrupt:
        print()
        print(
            "Build cancelado."
        )

        raise SystemExit(1)

    except Exception as exc:
        print()
        print("=" * 60)
        print(" ERRO NO BUILD")
        print("=" * 60)

        print()
        print(exc)

        print()

        raise SystemExit(1)


if __name__ == "__main__":
    main()