import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parent


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        base = Path(
            sys._MEIPASS
        )
    else:
        base = ROOT

    return (
        base
        / relative_path
    )


def build_screensaver(
    config,
    destination,
):
    destination = Path(
        destination
    ).resolve()

    if destination.suffix.lower() != ".scr":
        destination = (
            destination.with_suffix(
                ".scr"
            )
        )

    runtime_template = resource_path(
        "resources/OpenSCRRuntime.scr"
    )

    if not runtime_template.exists():
        if getattr(sys, "frozen", False):
            raise FileNotFoundError(
                "OpenSCRRuntime.scr não encontrado no aplicativo instalado."
            )

        build_runtime_script = ROOT / "build_runtime.py"
        if not build_runtime_script.exists():
            raise FileNotFoundError(
                "OpenSCRRuntime.scr não encontrado e build_runtime.py também não existe."
            )

        result = subprocess.run(
            [sys.executable, str(build_runtime_script)],
            cwd=str(ROOT),
            check=False,
        )
        if result.returncode != 0 or not runtime_template.exists():
            raise RuntimeError(
                "Não foi possível gerar automaticamente o runtime do OpenSCR."
            )

    data_dir = destination.with_name(
        f"{destination.stem}.data"
    )

    temp_root = Path(
        tempfile.mkdtemp(
            prefix="openscr_"
        )
    )

    try:
        temp_data = (
            temp_root
            / f"{destination.stem}.data"
        )

        assets_dir = (
            temp_data
            / "assets"
        )

        assets_dir.mkdir(
            parents=True
        )

        packaged_config = dict(
            config
        )

        packaged_images = []

        for index, image in enumerate(
            config.get(
                "images",
                [],
            )
        ):
            source = Path(
                image
            )

            if not source.exists():
                raise FileNotFoundError(
                    f"Imagem não encontrada:\n{source}"
                )

            extension = (
                source.suffix.lower()
            )

            filename = (
                f"image_{index:04d}"
                f"{extension}"
            )

            target = (
                assets_dir
                / filename
            )

            shutil.copy2(
                source,
                target,
            )

            packaged_images.append(
                f"assets/{filename}"
            )

        packaged_config[
            "images"
        ] = packaged_images

        config_file = (
            temp_data
            / "config.json"
        )

        with config_file.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                packaged_config,
                file,
                ensure_ascii=False,
                indent=4,
            )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if destination.exists():
            destination.unlink()

        if data_dir.exists():
            shutil.rmtree(
                data_dir
            )

        shutil.copy2(
            runtime_template,
            destination,
        )

        shutil.copytree(
            temp_data,
            data_dir,
        )

    finally:
        shutil.rmtree(
            temp_root,
            ignore_errors=True,
        )

    return (
        destination,
        data_dir,
    )