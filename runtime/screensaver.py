import math
import random

from PySide6.QtCore import (
    Qt,
    QRect,
    QRectF,
    Property,
    QPropertyAnimation,
    QEasingCurve,
    QTimer,
    QEvent,
)
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QLinearGradient,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import QWidget, QApplication

from runtime.variables import render_variables


TRANSITIONS = [
    "fade",
    "slide_left",
    "slide_right",
    "zoom",
    "gradient",
]


class ScreenSaverWindow(QWidget):
    def __init__(self, config, screen=None):
        super().__init__()

        self.config = config
        self.screen_target = screen

        self.images = []
        self.current_index = 0

        self.current_pixmap = None
        self.next_pixmap = None

        self.transition_name = "fade"
        self._progress = 0.0

        self.animation = None

        self.initial_mouse_position = QCursor.pos()
        self.exit_input_enabled = False

        self.setMouseTracking(True)

        app = QApplication.instance()

        if app:
            app.installEventFilter(self)

        self.load_images()
        self.setup_window()
        self.setup_timers()

    # ---------------------------------------------------------
    # WINDOW
    # ---------------------------------------------------------

    def setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        self.setCursor(Qt.CursorShape.BlankCursor)

        if self.screen_target:
            geometry = self.screen_target.geometry()
            self.setGeometry(geometry)

    # ---------------------------------------------------------
    # IMAGES
    # ---------------------------------------------------------

    def load_images(self):
        image_paths = self.config.get("images", [])

        for path in image_paths:
            pixmap = QPixmap(path)

            if not pixmap.isNull():
                self.images.append(pixmap)

        if self.images:
            self.current_pixmap = self.images[0]

    # ---------------------------------------------------------
    # TIMERS
    # ---------------------------------------------------------

    def setup_timers(self):
        display_seconds = self.config.get("display_seconds", 8)

        self.slide_timer = QTimer(self)
        self.slide_timer.setSingleShot(True)
        self.slide_timer.timeout.connect(self.start_next_image)

        self.slide_timer.start(int(display_seconds * 1000))

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update)
        self.clock_timer.start(500)

        self.input_timer = QTimer(self)

        self.input_timer.timeout.connect(
            self.check_mouse_position
        )

        self.input_timer.start(
            100
        )

        # Evita que o screensaver feche por eventos de mouse
        # gerados enquanto a janela está sendo aberta.
        QTimer.singleShot(
            1800,
            self.enable_input_exit,
        )

    # ---------------------------------------------------------
    # Filtro Global para Mouse e Teclado
    # ---------------------------------------------------------
    def eventFilter(
        self,
        watched,
        event,
    ):
        if not self.exit_input_enabled:
            return super().eventFilter(
                watched,
                event,
            )

        event_type = event.type()

        if event_type in (
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonDblClick,
        ):
            QApplication.quit()

            return True

        if event_type == QEvent.Type.KeyPress:
            QApplication.quit()

            return True

        return super().eventFilter(
            watched,
            event,
        )

    def enable_input_exit(self):
        self.initial_mouse_position = QCursor.pos()
        self.exit_input_enabled = True

    def check_mouse_position(self):
        if not self.exit_input_enabled:
            return

        if not self.config.get(
            "exit_on_mouse",
            True,
        ):
            return

        current = QCursor.pos()
        initial = self.initial_mouse_position

        dx = current.x() - initial.x()
        dy = current.y() - initial.y()

        distance = math.sqrt(
            (dx * dx)
            + (dy * dy)
        )

        threshold = self.config.get(
            "mouse_threshold",
            15,
        )

        if distance >= threshold:
            QApplication.quit()

    # ---------------------------------------------------------
    # TRANSITION
    # ---------------------------------------------------------

    def start_next_image(self):
        if len(self.images) <= 1:
            self.restart_slide_timer()
            return

        self.current_index += 1

        if self.current_index >= len(self.images):
            self.current_index = 0

        self.next_pixmap = self.images[self.current_index]

        configured_transition = self.config.get(
            "transition",
            "fade",
        )

        if configured_transition == "random":
            self.transition_name = random.choice(
                TRANSITIONS
            )
        else:
            self.transition_name = configured_transition

        self.setProgress(0)

        self.animation = QPropertyAnimation(
            self,
            b"progress",
        )

        duration = self.config.get(
            "transition_seconds",
            1.5,
        )

        self.animation.setDuration(
            int(duration * 1000)
        )

        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)

        self.animation.setEasingCurve(
            QEasingCurve.Type.InOutCubic
        )

        self.animation.finished.connect(
            self.finish_transition
        )

        self.animation.start()

    def finish_transition(self):
        self.current_pixmap = self.next_pixmap
        self.next_pixmap = None

        self.setProgress(0)

        self.restart_slide_timer()

    def restart_slide_timer(self):
        seconds = self.config.get(
            "display_seconds",
            8,
        )

        self.slide_timer.start(
            int(seconds * 1000)
        )

    # ---------------------------------------------------------
    # ANIMATION PROPERTY
    # ---------------------------------------------------------

    def getProgress(self):
        return self._progress

    def setProgress(self, value):
        self._progress = value
        self.update()

    progress = Property(
        float,
        getProgress,
        setProgress,
    )

    # ---------------------------------------------------------
    # PAINTING
    # ---------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        background = QColor(
            self.config.get(
                "background_color",
                "#000000",
            )
        )

        painter.fillRect(
            self.rect(),
            background,
        )

        if self.current_pixmap:
            self.draw_transition(painter)

        self.draw_text(painter)

    # ---------------------------------------------------------
    # IMAGE SCALING
    # ---------------------------------------------------------

    def get_scaled_pixmap(self, pixmap):
        if not pixmap:
            return None

        fit = self.config.get(
            "image_fit",
            "cover",
        )

        size = self.size()

        if fit == "contain":
            scaled = pixmap.scaled(
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            scaled = pixmap.scaled(
                size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )

        return scaled

    def centered_rect(self, pixmap):
        x = (
            self.width()
            - pixmap.width()
        ) // 2

        y = (
            self.height()
            - pixmap.height()
        ) // 2

        return QRect(
            x,
            y,
            pixmap.width(),
            pixmap.height(),
        )

    # ---------------------------------------------------------
    # TRANSITIONS
    # ---------------------------------------------------------

    def draw_transition(self, painter):
        current = self.get_scaled_pixmap(
            self.current_pixmap
        )

        if not current:
            return

        current_rect = self.centered_rect(
            current
        )

        if not self.next_pixmap:
            painter.drawPixmap(
                current_rect,
                current,
            )
            return

        next_image = self.get_scaled_pixmap(
            self.next_pixmap
        )

        next_rect = self.centered_rect(
            next_image
        )

        transition = self.transition_name
        progress = self._progress

        if transition == "fade":
            self.draw_fade(
                painter,
                current,
                next_image,
                current_rect,
                next_rect,
                progress,
            )

        elif transition == "slide_left":
            self.draw_slide_left(
                painter,
                current,
                next_image,
                progress,
            )

        elif transition == "slide_right":
            self.draw_slide_right(
                painter,
                current,
                next_image,
                progress,
            )

        elif transition == "zoom":
            self.draw_zoom(
                painter,
                current,
                next_image,
                current_rect,
                progress,
            )

        elif transition == "gradient":
            self.draw_gradient(
                painter,
                current,
                next_image,
                current_rect,
                next_rect,
                progress,
            )

        else:
            painter.drawPixmap(
                next_rect,
                next_image,
            )

    # ---------------------------------------------------------
    # FADE
    # ---------------------------------------------------------

    def draw_fade(
        self,
        painter,
        current,
        next_image,
        current_rect,
        next_rect,
        progress,
    ):
        painter.setOpacity(
            1.0 - progress
        )

        painter.drawPixmap(
            current_rect,
            current,
        )

        painter.setOpacity(progress)

        painter.drawPixmap(
            next_rect,
            next_image,
        )

        painter.setOpacity(1.0)

    # ---------------------------------------------------------
    # SLIDE LEFT
    # ---------------------------------------------------------

    def draw_slide_left(
        self,
        painter,
        current,
        next_image,
        progress,
    ):
        width = self.width()

        current_x = int(
            -width * progress
        )

        next_x = int(
            width * (1 - progress)
        )

        painter.drawPixmap(
            current_x,
            (self.height() - current.height()) // 2,
            current,
        )

        painter.drawPixmap(
            next_x,
            (self.height() - next_image.height()) // 2,
            next_image,
        )

    # ---------------------------------------------------------
    # SLIDE RIGHT
    # ---------------------------------------------------------

    def draw_slide_right(
        self,
        painter,
        current,
        next_image,
        progress,
    ):
        width = self.width()

        current_x = int(
            width * progress
        )

        next_x = int(
            -width * (1 - progress)
        )

        painter.drawPixmap(
            current_x,
            (self.height() - current.height()) // 2,
            current,
        )

        painter.drawPixmap(
            next_x,
            (self.height() - next_image.height()) // 2,
            next_image,
        )

    # ---------------------------------------------------------
    # ZOOM
    # ---------------------------------------------------------

    def draw_zoom(
        self,
        painter,
        current,
        next_image,
        current_rect,
        progress,
    ):
        painter.drawPixmap(
            current_rect,
            current,
        )

        scale = (
            0.85
            + (0.15 * progress)
        )

        width = int(
            next_image.width() * scale
        )

        height = int(
            next_image.height() * scale
        )

        scaled = next_image.scaled(
            width,
            height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        rect = self.centered_rect(
            scaled
        )

        painter.setOpacity(progress)

        painter.drawPixmap(
            rect,
            scaled,
        )

        painter.setOpacity(1)

    # ---------------------------------------------------------
    # GRADIENT
    # ---------------------------------------------------------

    def draw_gradient(
        self,
        painter,
        current,
        next_image,
        current_rect,
        next_rect,
        progress,
    ):
        painter.drawPixmap(
            current_rect,
            current,
        )

        width = self.width()

        reveal = int(
            width * progress
        )

        if reveal <= 0:
            return

        painter.save()

        painter.setClipRect(
            QRect(
                0,
                0,
                reveal,
                self.height(),
            )
        )

        painter.drawPixmap(
            next_rect,
            next_image,
        )

        painter.restore()

        # Pequena região em degradê na borda
        gradient_width = 120

        start_x = max(
            0,
            reveal - gradient_width,
        )

        gradient = QLinearGradient(
            start_x,
            0,
            reveal,
            0,
        )

        gradient.setColorAt(
            0,
            QColor(255, 255, 255, 0),
        )

        gradient.setColorAt(
            1,
            QColor(255, 255, 255, 100),
        )

        painter.fillRect(
            QRect(
                start_x,
                0,
                gradient_width,
                self.height(),
            ),
            gradient,
        )

    # ---------------------------------------------------------
    # TEXT
    # ---------------------------------------------------------

    def draw_text(self, painter):
        if not self.config.get(
            "text_enabled",
            True,
        ):
            return

        template = self.config.get(
            "text",
            "",
        )

        if not template:
            return

        text = render_variables(
            template
        )

        font_size = self.config.get(
            "text_size",
            32,
        )

        font = QFont(
            "Segoe UI",
            font_size,
        )

        painter.setFont(font)

        color = QColor(
            self.config.get(
                "text_color",
                "#FFFFFF",
            )
        )

        painter.setPen(color)

        margin = self.config.get(
            "text_margin",
            50,
        )

        rect = self.rect().adjusted(
            margin,
            margin,
            -margin,
            -margin,
        )

        position = self.config.get(
            "text_position",
            "bottom_right",
        )

        alignment = self.get_text_alignment(
            position
        )

        # sombra
        painter.setPen(
            QColor(0, 0, 0, 180)
        )

        shadow_rect = rect.translated(
            2,
            2,
        )

        painter.drawText(
            shadow_rect,
            alignment,
            text,
        )

        painter.setPen(color)

        painter.drawText(
            rect,
            alignment,
            text,
        )

    def get_text_alignment(self, position):
        positions = {
            "top_left":
                Qt.AlignmentFlag.AlignTop
                | Qt.AlignmentFlag.AlignLeft,

            "top_center":
                Qt.AlignmentFlag.AlignTop
                | Qt.AlignmentFlag.AlignHCenter,

            "top_right":
                Qt.AlignmentFlag.AlignTop
                | Qt.AlignmentFlag.AlignRight,

            "center":
                Qt.AlignmentFlag.AlignCenter,

            "bottom_left":
                Qt.AlignmentFlag.AlignBottom
                | Qt.AlignmentFlag.AlignLeft,

            "bottom_center":
                Qt.AlignmentFlag.AlignBottom
                | Qt.AlignmentFlag.AlignHCenter,

            "bottom_right":
                Qt.AlignmentFlag.AlignBottom
                | Qt.AlignmentFlag.AlignRight,
        }

        return positions.get(
            position,
            Qt.AlignmentFlag.AlignBottom
            | Qt.AlignmentFlag.AlignRight,
        )