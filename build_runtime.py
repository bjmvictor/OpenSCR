
import subprocess
import sys
import shutil
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parent

RUNTIME = (
    ROOT
    / "runtime"
    / "app.py"
)

RESOURCES = (
    ROOT
    / "resources"
)

BUILD = (
    ROOT
    / "build"
    / "runtime"
)

ICON = (
    ROOT
    / "assets"
    / "OpenSCR.ico"
)


def main():
    RESOURCES.mkdir(
        parents=True,
        exist_ok=True,
    )

    command = [
        sys.executable,
        "-m",
        "PyInstaller",

        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--noupx",

        "--name",
        "OpenSCRRuntime",

        "--distpath",
        str(RESOURCES),

        "--workpath",
        str(BUILD),

        "--specpath",
        str(BUILD),

        "--paths",
        str(ROOT),
    ]

    if ICON.exists():
        command.extend(
            [
                "--icon",
                str(ICON),
            ]
        )

    command.append(
        str(RUNTIME)
    )

    print(
        "Compilando OpenSCR Runtime..."
    )

    result = subprocess.run(
        command
    )

    if result.returncode != 0:
        raise SystemExit(
            "Falha ao compilar OpenSCR Runtime."
        )

    exe = (
        RESOURCES
        / "OpenSCRRuntime.exe"
    )

    scr = (
        RESOURCES
        / "OpenSCRRuntime.scr"
    )

    if not exe.exists():
        raise RuntimeError(
            "O PyInstaller não gerou OpenSCRRuntime.exe."
        )

    if scr.exists():
        scr.unlink()

    shutil.copy2(
        exe,
        scr,
    )

    print()
    print("Runtime criado com sucesso:")
    print(f"  EXE: {exe}")
    print(f"  SCR: {scr}")


if __name__ == "__main__":
    main()