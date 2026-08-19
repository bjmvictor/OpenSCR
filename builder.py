from native_builder import (
    build_native_screensaver,
)


def build_screensaver(
    config,
    destination,
):
    images = config.get(
        "images",
        []
    )


    if not images:
        raise RuntimeError(
            "Nenhuma imagem foi configurada."
        )


    margins = config.get("text_margin", 50)
    if isinstance(margins, dict):
        margin = min(
            int(margins.get(side, 50))
            for side in ("top", "right", "bottom", "left")
        )
    else:
        margin = int(margins)

    shadow = config.get(
        "text_shadow",
        {},
    )

    return build_native_screensaver(
        image_paths=images,

        destination=destination,

        display_seconds=float(
            config.get(
                "display_seconds",
                8
            )
        ),

        transition_seconds=float(
            config.get(
                "transition_seconds",
                1.5
            )
        ),

        transition=config.get(
            "transition",
            "random"
        ),

        fit=config.get(
            "image_fit",
            "cover"
        ),

        text=config.get(
            "text",
            ""
        ),

        text_enabled=bool(
            config.get(
                "text_enabled",
                True
            )
        ),

        text_size=int(
            config.get(
                "text_size",
                34
            )
        ),

        text_color=config.get(
            "text_color",
            "#FFFFFF"
        ),

        text_position=config.get(
            "text_position",
            "bottom_right"
        ),

        text_margin=margin,

        text_shadow_enabled=bool(
            shadow.get(
                "enabled",
                True,
            )
        ),

        text_shadow_color=shadow.get(
            "color",
            "#000000",
        ),

        text_shadow_offset_x=int(
            shadow.get(
                "offset_x",
                2,
            )
        ),

        text_shadow_offset_y=int(
            shadow.get(
                "offset_y",
                2,
            )
        ),

        text_shadow_opacity=int(
            shadow.get(
                "opacity",
                180,
            )
        ),

        image_order=config.get(
            "image_order",
            "forward",
        ),
    )