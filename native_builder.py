import argparse
import ctypes
import shutil
import struct
import sys

from pathlib import Path


# ============================================================
# OpenSCR Native Builder
# ============================================================

ROOT = Path(
    __file__
).resolve().parent


def resource_path(
    relative_path,
):
    if getattr(
        sys,
        "frozen",
        False,
    ):
        base = Path(
            sys._MEIPASS
        )

    else:
        base = ROOT


    return (
        base
        /
        relative_path
    )


def get_runtime_template():
    return resource_path(
        "resources/OpenSCRNativeRuntime.exe"
    )


# ============================================================
# Resource IDs
# ============================================================

RT_RCDATA = 10

RESOURCE_CONFIG = 900

RESOURCE_TEXT = 901
RESOURCE_TEXT_CONFIG = 902

RESOURCE_IMAGE_START = 1000


# "OSCR" em little endian
CONFIG_MAGIC = 0x5243534F

CONFIG_VERSION = 3


# ============================================================
# Windows API
# ============================================================

kernel32 = ctypes.WinDLL(
    "kernel32",
    use_last_error=True,
)


kernel32.BeginUpdateResourceW.argtypes = [
    ctypes.c_wchar_p,
    ctypes.c_bool,
]

kernel32.BeginUpdateResourceW.restype = (
    ctypes.c_void_p
)


kernel32.UpdateResourceW.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_ushort,
    ctypes.c_void_p,
    ctypes.c_uint32,
]

kernel32.UpdateResourceW.restype = (
    ctypes.c_bool
)


kernel32.EndUpdateResourceW.argtypes = [
    ctypes.c_void_p,
    ctypes.c_bool,
]

kernel32.EndUpdateResourceW.restype = (
    ctypes.c_bool
)


# ============================================================
# Helpers
# ============================================================

def make_int_resource(value):
    return ctypes.c_void_p(
        value
    )

def parse_color(
    value,
):
    value = (
        value
        .strip()
        .lstrip("#")
    )

    if len(value) == 6:
        return (
            0xFF000000
            |
            int(
                value,
                16,
            )
        )

    if len(value) == 8:
        return int(
            value,
            16,
        )

    raise ValueError(
        (
            "Cor inválida. "
            "Use #RRGGBB."
        )
    )

def build_text_config(
    enabled,
    font_size,
    color,
    position,
    margin_top,
    margin_right,
    margin_bottom,
    margin_left,

    shadow_enabled=True,
    shadow_color="#000000",
    shadow_offset_x=2,
    shadow_offset_y=2,
    shadow_opacity=180,
):
    positions = {
        "top_left": 0,
        "top_center": 1,
        "top_right": 2,
        "center": 3,
        "bottom_left": 4,
        "bottom_center": 5,
        "bottom_right": 6,
    }

    return struct.pack(
        "<10I2iI",

        1 if enabled else 0,

        int(font_size),

        parse_color(
            color
        ),

        positions[
            position
        ],

        int(margin_top),
        int(margin_right),
        int(margin_bottom),
        int(margin_left),

        1 if shadow_enabled else 0,

        parse_color(
            shadow_color
        ),

        int(
            shadow_offset_x
        ),

        int(
            shadow_offset_y
        ),

        max(
            0,
            min(
                255,
                int(shadow_opacity),
            ),
        ),
    )
    

def raise_last_error(operation):
    error = ctypes.get_last_error()

    raise OSError(
        error,
        (
            f"{operation} falhou. "
            f"Erro Win32: {error}"
        ),
    )


# ============================================================
# Resource transaction
# ============================================================

def inject_resources(
    executable,
    resources,
):
    executable = Path(
        executable
    ).resolve()

    update_handle = (
        kernel32.BeginUpdateResourceW(
            str(executable),
            False,
        )
    )

    if not update_handle:
        raise_last_error(
            "BeginUpdateResourceW"
        )

    committed = False

    try:
        buffers = []

        for resource_id, data in resources:
            buffer = (
                ctypes.c_ubyte
                *
                len(data)
            ).from_buffer_copy(
                data
            )

            # Mantém o buffer vivo durante a operação.
            buffers.append(
                buffer
            )

            success = (
                kernel32.UpdateResourceW(
                    update_handle,

                    make_int_resource(
                        RT_RCDATA
                    ),

                    make_int_resource(
                        resource_id
                    ),

                    0,

                    ctypes.cast(
                        buffer,
                        ctypes.c_void_p,
                    ),

                    len(data),
                )
            )

            if not success:
                raise_last_error(
                    (
                        "UpdateResourceW "
                        f"(resource {resource_id})"
                    )
                )

        success = (
            kernel32.EndUpdateResourceW(
                update_handle,
                False,
            )
        )

        if not success:
            raise_last_error(
                "EndUpdateResourceW"
            )

        committed = True

    finally:
        if (
            update_handle
            and
            not committed
        ):
            kernel32.EndUpdateResourceW(
                update_handle,
                True,
            )


# ============================================================
# Config
# ============================================================

def build_transition_mask(effects, random_enabled):
    effect_bits = {
        "fade": 1 << 0,
        "slide_left": 1 << 1,
        "slide_right": 1 << 2,
        "zoom": 1 << 3,
        "gradient": 1 << 4,
        "slide_up": 1 << 5,
        "slide_down": 1 << 6,
        "pixel": 1 << 7,
        "dissolve": 1 << 8,
        "glitch": 1 << 9,
        "blinds": 1 << 10,
    }
    if effects is None:
        return 0x7FF if random_enabled else 0
    mask = 0
    for effect in effects:
        mask |= effect_bits.get(effect, 0)
    return mask

def build_config(
    image_count,
    display_seconds,
    transition_seconds,
    transition,
    fit,
    image_order,
    transition_mask,
    background_color,
):
    transition_modes = {
        "fade": 0,
        "slide_left": 1,
        "slide_right": 2,
        "zoom": 3,
        "gradient": 4,
        "slide_up": 5,
        "slide_down": 6,
        "pixel": 7,
        "dissolve": 8,
        "glitch": 9,
        "blinds": 10,
        "random": 11,
    }

    fit_modes = {
        "cover": 0,
        "contain": 1,
    }

    order_modes = {
        "forward": 0,
        "reverse": 1,
        "random": 2,
    }

    transition_mode = (
        transition_modes[
            transition
        ]
    )

    order_mode = order_modes[
        image_order
    ]

    fit_mode = (
        fit_modes[
            fit
        ]
    )

    display_ms = int(
        display_seconds
        *
        1000
    )

    transition_ms = int(
        transition_seconds
        *
        1000
    )

    return struct.pack(
        "<10I",

        CONFIG_MAGIC,
        CONFIG_VERSION,

        image_count,

        display_ms,
        transition_ms,

        transition_mode,
        fit_mode,
        order_mode,
        transition_mask,
        parse_color(background_color),
    )

# ============================================================
# Build
# ============================================================

def build_native_screensaver(
    image_paths,
    destination,

    display_seconds=8,
    transition_seconds=1.5,

    transition="fade",
    fit="cover",

    image_order="forward",
    transition_effects=None,
    transition_random=False,
    background_color="#000000",

    text="",
    text_enabled=True,

    text_size=32,
    text_color="#FFFFFF",

    text_position="bottom_right",
    text_margin_top=50,
    text_margin_right=50,
    text_margin_bottom=50,
    text_margin_left=50,

    text_shadow_enabled=True,
    text_shadow_color="#000000",
    text_shadow_offset_x=2,
    text_shadow_offset_y=2,
    text_shadow_opacity=180,
):
    destination = Path(
        destination
    ).resolve()

    if (
        destination.suffix.lower()
        !=
        ".scr"
    ):
        destination = (
            destination.with_suffix(
                ".scr"
            )
        )

    template = (
        get_runtime_template()
    )

    if not template.exists():
        raise FileNotFoundError(
            (
                "OpenSCRNativeRuntime.exe "
                "não encontrado.\n\n"
                "Execute primeiro:\n"
                "python build_native_runtime.py"
            )
        )

    images = [
        Path(path).resolve()
        for path in image_paths
    ]

    if not images:
        raise RuntimeError(
            "Informe pelo menos uma imagem."
        )

    for image in images:
        if not image.exists():
            raise FileNotFoundError(
                f"Imagem não encontrada:\n{image}"
            )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        template,
        destination,
    )

    # --------------------------------------------------------
    # Config
    # --------------------------------------------------------

    config_data = build_config(
        image_count=len(images),

        display_seconds=display_seconds,
        transition_seconds=transition_seconds,

        transition=transition,
        fit=fit,
        image_order=image_order,
        transition_mask=build_transition_mask(
            transition_effects,
            transition_random or transition == "random",
        ),
        background_color=background_color,
    )

    text_config_data = (
        build_text_config(
            enabled=(
                text_enabled
                and
                bool(text)
            ),

            font_size=text_size,

            color=text_color,

            position=text_position,

            margin_top=text_margin_top,
            margin_right=text_margin_right,
            margin_bottom=text_margin_bottom,
            margin_left=text_margin_left,

            shadow_enabled=text_shadow_enabled,
            shadow_color=text_shadow_color,
            shadow_offset_x=text_shadow_offset_x,
            shadow_offset_y=text_shadow_offset_y,
            shadow_opacity=text_shadow_opacity,
        )
    )


    resources = [
        (
            RESOURCE_CONFIG,
            config_data,
        ),

        (
            RESOURCE_TEXT_CONFIG,
            text_config_data,
        ),
    ]

    if (
        text_enabled
        and
        text
    ):
        text_data = (
            text.encode(
                "utf-16-le"
            )
        )


        resources.append(
            (
                RESOURCE_TEXT,
                text_data,
            )
        )

    # --------------------------------------------------------
    # Images
    # --------------------------------------------------------

    total_image_bytes = 0

    for index, image in enumerate(
        images
    ):
        data = image.read_bytes()

        total_image_bytes += len(
            data
        )

        resources.append(
            (
                RESOURCE_IMAGE_START
                +
                index,

                data,
            )
        )

    # --------------------------------------------------------
    # Inject
    # --------------------------------------------------------

    inject_resources(
        destination,
        resources,
    )

    size_mb = (
        destination.stat().st_size
        /
        1024
        /
        1024
    )

    image_size_mb = (
        total_image_bytes
        /
        1024
        /
        1024
    )

    print()
    print("=" * 60)
    print("OpenSCR Native Builder")
    print("=" * 60)

    print()
    print(
        f"Arquivo: {destination}"
    )

    print(
        f"Imagens: {len(images)}"
    )

    print(
        f"Tamanho das imagens: "
        f"{image_size_mb:.2f} MB"
    )

    print(
        f"Tamanho final: "
        f"{size_mb:.2f} MB"
    )

    print(
        f"Exibição: "
        f"{display_seconds:.1f}s"
    )

    print(
        f"Transição: "
        f"{transition_seconds:.1f}s"
    )

    print(
        f"Ajuste: {fit}"
    )

    print()

    return destination


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "OpenSCR Native Builder"
        )
    )

    parser.add_argument(
        "output",
        help="Arquivo .scr de saída",
    )

    parser.add_argument(
        "images",
        nargs="+",
        help="Imagens JPG/PNG",
    )

    parser.add_argument(
        "--text",
        default="",
        help="Texto exibido na tela",
    )


    parser.add_argument(
        "--text-size",
        type=int,
        default=32,
    )


    parser.add_argument(
        "--text-color",
        default="#FFFFFF",
    )


    parser.add_argument(
        "--text-position",
        choices=[
            "top_left",
            "top_center",
            "top_right",

            "center",

            "bottom_left",
            "bottom_center",
            "bottom_right",
        ],
        default="bottom_right",
    )


    parser.add_argument(
        "--text-margin",
        type=int,
        default=50,
    )

    parser.add_argument(
        "--display",
        type=float,
        default=8.0,
        help=(
            "Tempo de exibição "
            "em segundos"
        ),
    )

    parser.add_argument(
        "--transition",
        type=float,
        default=1.5,
        help=(
            "Duração da transição "
            "em segundos"
        ),
    )

    parser.add_argument(
        "--fit",
        choices=[
            "cover",
            "contain",
        ],
        default="cover",
    )

    parser.add_argument(
        "--effect",
        choices=[
            "fade",
            "slide_left",
            "slide_right",
            "zoom",
            "gradient",
            "pixel",
            "dissolve",
            "glitch",
            "blinds",
            "random",
        ],
        default="random",
    )

    args = parser.parse_args()

    build_native_screensaver(
        image_paths=args.images,

        destination=args.output,

        display_seconds=args.display,

        transition_seconds=args.transition,

        transition=args.effect,

        fit=args.fit,

        text=args.text,

        text_enabled=True,

        text_size=args.text_size,

        text_color=args.text_color,

        text_position=args.text_position,

        text_margin_top=args.text_margin,
        text_margin_right=args.text_margin,
        text_margin_bottom=args.text_margin,
        text_margin_left=args.text_margin,
    )


if __name__ == "__main__":
    main()
