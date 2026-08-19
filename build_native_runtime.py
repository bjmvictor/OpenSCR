import shutil
import subprocess
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parent


SOURCE_DIR = (
    ROOT
    / "native"
    / "runtime"
)


BUILD_DIR = (
    ROOT
    / "build"
    / "native-runtime"
)


RESOURCES_DIR = (
    ROOT
    / "resources"
)


OUTPUT_FILE = (
    RESOURCES_DIR
    / "OpenSCRNativeRuntime.exe"
)


def run(
    command,
):
    print()

    print(
        " ".join(
            str(item)
            for item in command
        )
    )

    print()

    subprocess.run(
        command,
        check=True,
    )


def main():
    print()
    print(
        "OpenSCR Native Runtime"
    )

    print(
        "=" * 50
    )


    RESOURCES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    # --------------------------------------------------------
    # Configure
    # --------------------------------------------------------

    run(
        [
            "cmake",

            "-S",
            str(SOURCE_DIR),

            "-B",
            str(BUILD_DIR),
        ]
    )


    # --------------------------------------------------------
    # Build
    # --------------------------------------------------------

    run(
        [
            "cmake",

            "--build",
            str(BUILD_DIR),

            "--config",
            "Release",

            "--parallel",
        ]
    )


    # --------------------------------------------------------
    # Find generated EXE
    # --------------------------------------------------------

    candidates = list(
        BUILD_DIR.rglob(
            "OpenSCRNativeRuntime.exe"
        )
    )


    if not candidates:
        raise FileNotFoundError(
            (
                "OpenSCRNativeRuntime.exe "
                "não foi encontrado após o build."
            )
        )


    generated = candidates[0]


    shutil.copy2(
        generated,
        OUTPUT_FILE,
    )


    size_kb = (
        OUTPUT_FILE.stat().st_size
        /
        1024
    )


    print()
    print(
        "=" * 50
    )

    print(
        "Runtime nativo criado:"
    )

    print(
        OUTPUT_FILE
    )

    print(
        f"Tamanho: {size_kb:.2f} KB"
    )

    print(
        "=" * 50
    )


if __name__ == "__main__":
    main()