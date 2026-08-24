
import os
import shutil
import subprocess
import sys
import platform
from pathlib import Path


# ============================================================
# OpenSCR Build Configuration
# ============================================================

APP_NAME = "OpenSCR"
APP_VERSION = "2.0.5"


ROOT_DIR = Path(
    __file__
).resolve().parent


CREATOR_FILE = (
    ROOT_DIR
    / "creator.py"
)

RUNTIME_HOOK_FILE = ROOT_DIR / "pyinstaller_runtime_hook.py"


ASSETS_DIR = (
    ROOT_DIR
    / "assets"
)

LOCALES_DIR = ROOT_DIR / "locales"


ICON_FILE = (
    ASSETS_DIR
    / "OpenSCR.ico"
)


SPLASH_FILE = (
    ASSETS_DIR
    / "splash.png"
)


RESOURCES_DIR = (
    ROOT_DIR
    / "resources"
)


RUNTIME_NATIVE = (
    RESOURCES_DIR
    /
    "OpenSCRNativeRuntime.exe"
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
    required_files = [CREATOR_FILE, RUNTIME_HOOK_FILE]
    if sys.platform == "win32":
        required_files.append(RUNTIME_NATIVE)

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
            "  python build_native_runtime.py"
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

    if DIST_DIR.exists():
        shutil.rmtree(
            DIST_DIR,
            ignore_errors=True,
        )

    if RELEASE_DIR.exists():
        shutil.rmtree(
            RELEASE_DIR,
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

    onefile = os.environ.get("OPENSCR_ONEFILE", "").lower() in (
        "1",
        "true",
        "yes",
    )

    import PySide2  # noqa: F401

    command = [
        sys.executable,
        "-m",
        "PyInstaller",

        "--noconfirm",
        "--clean",

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
        "--runtime-hook",
        str(RUNTIME_HOOK_FILE),

        # Include shiboken's native support binaries explicitly. PyInstaller's
        # Qt hooks select the Qt DLLs/plugins used by the imported modules.
        "--collect-binaries",
        "shiboken2",
        "--hidden-import",
        "PySide2.QtCore",
        "--hidden-import",
        "PySide2.QtGui",
        "--hidden-import",
        "PySide2.QtWidgets",
        "--exclude-module",
        "numpy",
        "--exclude-module",
        "PIL",
    ]

    command.append("--onefile" if onefile else "--onedir")

    native_splash = os.environ.get("OPENSCR_NATIVE_SPLASH", "").lower() in (
        "1", "true", "yes",
    )
    if SPLASH_FILE.exists() and native_splash:
        command.extend(
            [
                "--splash",
                str(SPLASH_FILE),
            ]
        )

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

    if sys.platform == "win32":
        add_data_argument(command, RUNTIME_NATIVE, "resources")

    # --------------------------------------------------------
    # Assets
    # --------------------------------------------------------

    if ASSETS_DIR.exists():
        add_data_argument(
            command,
            ASSETS_DIR,
            "assets",
        )
    if LOCALES_DIR.exists():
        add_data_argument(command, LOCALES_DIR, "locales")

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

    executable_name = APP_NAME + (".exe" if sys.platform == "win32" else "")
    generated_exe = (
        DIST_DIR
        / executable_name
        if onefile
        else DIST_DIR
        / APP_NAME
        / executable_name
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

    if onefile:
        system_tag = "Windows" if sys.platform == "win32" else "Linux"
        arch_tag = platform.machine().lower()
        extension = ".exe" if sys.platform == "win32" else ""
        portable_name = f"{APP_NAME}-{APP_VERSION}-{system_tag}-{arch_tag}-Portable{extension}"
        portable_file = RELEASE_DIR / portable_name
        if portable_file.exists():
            portable_file.unlink()
        shutil.copy2(generated_exe, portable_file)
    else:
        system_tag = "Windows" if sys.platform == "win32" else "Linux"
        arch_tag = platform.machine().lower()
        portable_dir = RELEASE_DIR / f"{APP_NAME}-{APP_VERSION}-{system_tag}-{arch_tag}-Portable"
        if portable_dir.exists():
            shutil.rmtree(portable_dir, ignore_errors=True)
        shutil.copytree(DIST_DIR / APP_NAME, portable_dir)
        portable_file = portable_dir / executable_name

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

    print(f"Tamanho: {size_mb:.2f} MB")
    if not onefile:
        print("Modo: onedir (inicialização rápida)")

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
