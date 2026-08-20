import ctypes
import importlib
import json
import re
import sys
import tempfile

from builder import (
    build_screensaver,
)
from build_worker import (
    ScrBuildThread,
)
from pathlib import Path
from PySide6.QtCore import (
    Qt,
    QProcess,
    QSize,
    QSettings,
    QTimer,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QIcon,
    QPixmap,
    QTextCharFormat,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QSplashScreen,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
    QListView
)
from PySide6.QtWidgets import QSizePolicy

from openscr_variables import (
    AVAILABLE_VARIABLES,
)

# -----------------------------------------------------
# ASSETS / APPID
# -----------------------------------------------------

def configure_windows_app_id():
    if sys.platform != "win32":
        return

    app_id = "bjmvictor.OpenSCR"

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            app_id
        )
    except Exception:
        pass

def resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent

    return base_path / relative_path

class OpenSCRCreator(
    QMainWindow
):
    def __init__(self):
        super().__init__()
        self.build_thread = None
        self.preview_process = None
        self.preview_output = ""
        self.current_project_path = None
        self.recent_menu = None
        self.loading_index = 0
        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self.update_loading_indicator)

        self.images = []

        self.text_color = (
            "#FFFFFF"
        )

        self.shadow_color = "#000000"
        self.background_color = "#000000"

        self.setWindowTitle(
            "OpenSCR"
        )

        icon_path = resource_path(
            "assets/OpenSCR.ico"
        )

        if icon_path.exists():
            self.setWindowIcon(
                QIcon(str(icon_path))
            )

        self.resize(
            1050,
            720,
        )

        self.setup_ui()

    # -----------------------------------------------------
    # UI
    # -----------------------------------------------------

    def setup_ui(self):
        self.setup_menu()
        central = QWidget()

        self.setCentralWidget(
            central
        )

        main_layout = QVBoxLayout(
            central
        )
        main_layout.setContentsMargins(6, 4, 6, 6)
        main_layout.setSpacing(6)

        title = QLabel(
            "OpenSCR"
        )

        title.setStyleSheet(
            """
            font-size: 26px;
            font-weight: 600;
            """
        )

        subtitle = QLabel(
            "Open Source Windows Screensaver Creator"
        )

        subtitle.setStyleSheet(
            "color: #777;"
        )

        header = QHBoxLayout()

        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand.addWidget(title)
        brand.addWidget(subtitle)

        header.addLayout(brand)
        header.addStretch()

        self.preview_button = QPushButton(
            "▶ Visualizar"
        )

        self.build_button = QPushButton(
            "Gerar .SCR"
        )

        self.preview_button.clicked.connect(
            self.preview
        )

        self.build_button.clicked.connect(
            self.build_scr
        )

        header.addWidget(
            self.preview_button
        )

        header.addWidget(
            self.build_button
        )

        self.loading_label = QLabel()
        self.loading_label.setMinimumWidth(110)
        self.loading_label.setVisible(False)
        header.addWidget(self.loading_label)

        header.setContentsMargins(0, 0, 0, 4)
        header.setSpacing(6)

        main_layout.addLayout(
            header
        )

        splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        main_layout.addWidget(
            splitter,
            1,
        )

        left = self.create_left_panel()
        right = self.create_right_panel()

        splitter.addWidget(left)
        splitter.addWidget(right)

        splitter.setSizes(
            [500, 500]
        )
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

    def setup_menu(self):
        file_menu = self.menuBar().addMenu("Arquivo")

        open_action = QAction("Abrir projeto...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(
            lambda checked=False: self.import_project()
        )
        file_menu.addAction(open_action)

        self.recent_menu = file_menu.addMenu("Recentes")
        self.update_recent_projects_menu()
        file_menu.addSeparator()

        save_action = QAction("Salvar", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        save_as_action = QAction("Salvar como...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()

        exit_action = QAction("Sair", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    # -----------------------------------------------------
    # LEFT PANEL
    # -----------------------------------------------------

    def create_left_panel(self):
        panel = QWidget()

        layout = QVBoxLayout(
            panel
        )

        # Images
        image_group = QGroupBox(
            "Imagens"
        )

        image_layout = QVBoxLayout(
            image_group
        )

        self.image_list = (
            QListWidget()
        )

        image_layout.addWidget(
            self.image_list
        )

        self.image_list.setDragEnabled(
            True
        )

        self.image_list.setAcceptDrops(
            True
        )

        self.image_list.setDropIndicatorShown(
            True
        )

        self.image_list.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )

        self.image_list.setDefaultDropAction(
            Qt.DropAction.MoveAction
        )


        self.image_list.model().rowsMoved.connect(
            self.sync_images_from_widget
        )

        image_buttons = QHBoxLayout()

        self.image_view_mode = QComboBox()

        self.image_view_mode.addItem(
            "Lista",
            "list",
        )

        self.image_view_mode.addItem(
            "Grade",
            "grid",
        )

        self.image_view_mode.currentIndexChanged.connect(
            self.update_image_view_mode
        )

        add_image = QPushButton(
            "Adicionar"
        )

        remove_image = QPushButton(
            "Remover"
        )

        add_image.clicked.connect(
            self.add_images
        )

        remove_image.clicked.connect(
            self.remove_image
        )

        image_buttons.addStretch()

        image_buttons.addWidget(
            self.image_view_mode
        )

        image_buttons.addWidget(
            QLabel("Ordem:")
        )

        self.image_order = QComboBox()
        self.image_order.addItem("Ordenado", "forward")
        self.image_order.addItem("Reverso", "reverse")
        self.image_order.addItem("Aleatório", "random")
        image_buttons.addWidget(self.image_order)

        image_buttons.addWidget(
            add_image
        )

        image_buttons.addWidget(
            remove_image
        )

        image_layout.addLayout(
            image_buttons
        )

        layout.addWidget(
            image_group
        )

        # Animation
        animation_group = QGroupBox(
            "Exibição e transição"
        )

        animation_form = QFormLayout(
            animation_group
        )

        self.display_time = (
            QDoubleSpinBox()
        )

        self.display_time.setRange(
            1,
            3600,
        )

        self.display_time.setValue(
            8
        )

        self.display_time.setSuffix(
            " s"
        )

        self.transition_time = (
            QDoubleSpinBox()
        )

        self.transition_time.setRange(
            0.1,
            30,
        )

        self.transition_time.setValue(
            1.5
        )

        self.transition_time.setSuffix(
            " s"
        )

        self.transition = QComboBox()

        self.transition.addItem(
            "Aleatório",
            "random",
        )

        self.transition.addItem(
            "Fade",
            "fade",
        )

        self.transition.addItem(
            "Degradê",
            "gradient",
        )

        self.transition.addItem(
            "Deslizar para esquerda",
            "slide_left",
        )

        self.transition.addItem(
            "Deslizar para direita",
            "slide_right",
        )

        self.transition.addItem(
            "Zoom",
            "zoom",
        )

        self.image_fit = QComboBox()

        self.image_fit.addItem(
            "Preencher tela",
            "cover",
        )

        self.image_fit.addItem(
            "Conter imagem",
            "contain",
        )

        animation_form.addRow(
            "Duração:",
            self.display_time,
        )

        animation_form.addRow(
            "Transição:",
            self.transition,
        )

        animation_form.addRow(
            "Duração transição:",
            self.transition_time,
        )

        animation_form.addRow(
            "Ajuste da imagem:",
            self.image_fit,
        )

        layout.addWidget(
            animation_group
        )

        background_group = QGroupBox("Fundo")
        background_form = QFormLayout(background_group)
        self.background_button = QPushButton("#000000")
        self.background_button.clicked.connect(self.select_background_color)
        self.background_preview = QLabel()
        self.background_preview.setFixedWidth(34)
        self.background_preview.setStyleSheet(
            "background-color: #000000; border: 1px solid #777;"
        )
        background_layout = QHBoxLayout()
        background_layout.addWidget(self.background_preview)
        background_layout.addWidget(self.background_button)
        background_form.addRow("Cor padrão:", background_layout)
        layout.addWidget(background_group)

        effects_group = QGroupBox("Efeitos de transição")
        effects_layout = QVBoxLayout(effects_group)
        self.effects_list = QListWidget()
        for label, value in (
            ("Fade", "fade"),
            ("Degradê", "gradient"),
            ("Deslizar para esquerda", "slide_left"),
            ("Deslizar para direita", "slide_right"),
            ("Zoom", "zoom"),
            ("Deslizar para cima", "slide_up"),
            ("Deslizar para baixo", "slide_down"),
        ):
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.effects_list.addItem(item)
        effects_layout.addWidget(self.effects_list)

        effect_buttons = QHBoxLayout()
        all_effects = QPushButton("Todos")
        no_effects = QPushButton("Nenhum")
        all_effects.clicked.connect(lambda: self.set_effects_checked(True))
        no_effects.clicked.connect(lambda: self.set_effects_checked(False))
        effect_buttons.addWidget(all_effects)
        effect_buttons.addWidget(no_effects)
        effects_layout.addLayout(effect_buttons)

        self.random_effects = QCheckBox("Escolher aleatoriamente")
        effects_layout.addWidget(self.random_effects)
        layout.addWidget(effects_group)

        return panel

    # -----------------------------------------------------
    # RIGHT PANEL
    # -----------------------------------------------------

    def create_right_panel(self):
        content = QWidget()

        layout = QVBoxLayout(
            content
        )
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        text_group = QGroupBox(
            "Texto sobre a tela"
        )

        text_layout = QVBoxLayout(
            text_group
        )

        self.text_enabled = QCheckBox(
            "Exibir texto"
        )

        self.text_enabled.setChecked(
            True
        )

        text_layout.addWidget(
            self.text_enabled
        )

        self.text_edit = QTextEdit()
        self.text_edit.setMinimumHeight(120)
        self.text_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.text_edit.setPlaceholderText(
            "Digite seu texto aqui...\n\n"
            "Exemplo:\n"
            "Hoje é {weekday}, {date}\n"
            "{time_seconds}"
        )

        self.text_edit.setPlainText(
            "{weekday}, {date}\n"
            "{time_seconds}"
        )

        text_layout.addWidget(
            self.text_edit
        )

        format_bar = QHBoxLayout()
        bold_button = QPushButton("B")
        italic_button = QPushButton("I")
        self.inline_size = QSpinBox()
        self.inline_size.setRange(8, 200)
        self.inline_size.setValue(48)
        size_button = QPushButton("Aplicar tamanho")
        bold_button.clicked.connect(self.apply_inline_bold)
        italic_button.clicked.connect(self.apply_inline_italic)
        size_button.clicked.connect(self.apply_inline_size)
        format_bar.addWidget(bold_button)
        format_bar.addWidget(italic_button)
        format_bar.addWidget(self.inline_size)
        format_bar.addWidget(size_button)
        text_layout.addLayout(format_bar)

        form = QFormLayout()

        self.text_position = (
            QComboBox()
        )

        positions = [
            (
                "Superior esquerdo",
                "top_left",
            ),
            (
                "Superior central",
                "top_center",
            ),
            (
                "Superior direito",
                "top_right",
            ),
            (
                "Centro",
                "center",
            ),
            (
                "Inferior esquerdo",
                "bottom_left",
            ),
            (
                "Inferior central",
                "bottom_center",
            ),
            (
                "Inferior direito",
                "bottom_right",
            ),
        ]

        for label, value in positions:
            self.text_position.addItem(
                label,
                value,
            )

        self.text_position.setCurrentIndex(
            6
        )

        self.text_size = QSpinBox()

        self.text_size.setRange(
            8,
            200,
        )

        self.text_size.setValue(
            32
        )

        self.color_button = QPushButton(
            "#FFFFFF"
        )

        self.color_button.clicked.connect(
            self.select_color
        )

        self.color_preview = QLabel()
        self.color_preview.setFixedWidth(34)
        self.color_preview.setStyleSheet(
            "background-color: #FFFFFF; border: 1px solid #777;"
        )

        color_layout = QHBoxLayout()
        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.color_button)

        self.margin_top = QSpinBox()
        self.margin_right = QSpinBox()
        self.margin_bottom = QSpinBox()
        self.margin_left = QSpinBox()
        for margin in (
            self.margin_top,
            self.margin_right,
            self.margin_bottom,
            self.margin_left,
        ):
            margin.setRange(0, 2000)
            margin.setValue(50)

        margins_layout = QHBoxLayout()
        for label, margin in (
            ("Sup", self.margin_top),
            ("Dir", self.margin_right),
            ("Inf", self.margin_bottom),
            ("Esq", self.margin_left),
        ):
            margins_layout.addWidget(QLabel(label))
            margins_layout.addWidget(margin)

        self.shadow_enabled = QCheckBox(
            "Sombra ativa"
        )

        self.shadow_enabled.setChecked(
            False
        )


        self.shadow_color_button = QPushButton(
            "#000000"
        )

        self.shadow_color_button.clicked.connect(
            self.select_shadow_color
        )


        self.shadow_x = QSpinBox()
        self.shadow_y = QSpinBox()

        for offset in (
            self.shadow_x,
            self.shadow_y,
        ):
            offset.setRange(
                -100,
                100,
            )

            offset.setValue(
                2
            )


        self.shadow_opacity = QSpinBox()

        self.shadow_opacity.setRange(
            0,
            255,
        )

        self.shadow_opacity.setValue(
            180
        )

        self.shadow_options = QWidget()

        shadow_form = QFormLayout(
            self.shadow_options
        )

        shadow_form.setContentsMargins(
            0,
            0,
            0,
            0,
        )


        shadow_form.addRow(
            "Cor da sombra:",
            self.shadow_color_button,
        )


        shadow_form.addRow(
            "Deslocamento X/Y:",
            self.create_shadow_offset_layout(),
        )


        shadow_form.addRow(
            "Opacidade:",
            self.shadow_opacity,
        )

        form.addRow(
            "Posição:",
            self.text_position,
        )

        form.addRow(
            "Tamanho:",
            self.text_size,
        )

        form.addRow(
            "Cor:",
            color_layout,
        )

        form.addRow(
            "Margens (sup/dir/inf/esq):",
            margins_layout,
        )

        form.addRow(
            "Sombra:",
            self.shadow_enabled,
        )
        form.addRow(
            self.shadow_options,
        )

        self.shadow_enabled.toggled.connect(
            self.shadow_options.setVisible
        )

        self.shadow_options.setVisible(
            self.shadow_enabled.isChecked()
        )

        text_layout.addLayout(
            form
        )

        layout.addWidget(
            text_group
        )

        variables_group = QGroupBox(
            "Variáveis disponíveis"
        )

        variables_layout = QVBoxLayout(
            variables_group
        )

        info = QLabel(
            "Dê duplo clique para inserir "
            "uma variável no texto."
        )

        info.setWordWrap(True)

        variables_layout.addWidget(
            info
        )

        self.variables_list = (
            QListWidget()
        )

        for variable, description in (
            AVAILABLE_VARIABLES.items()
        ):
            self.variables_list.addItem(
                f"{variable}  —  {description}"
            )

        self.variables_list.itemDoubleClicked.connect(
            self.insert_variable
        )

        variables_layout.addWidget(
            self.variables_list
        )

        layout.addWidget(
            variables_group
        )

        return content

    def create_shadow_offset_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(self.shadow_x)
        layout.addWidget(QLabel("/"))
        layout.addWidget(self.shadow_y)
        return layout

    def set_effects_checked(self, checked):
        for index in range(self.effects_list.count()):
            self.effects_list.item(index).setCheckState(
                Qt.CheckState.Checked
                if checked else Qt.CheckState.Unchecked
            )

    def refresh_image_list(self):
        self.image_list.clear()

        for path in self.images:
            self.image_list.addItem(
                self.create_image_item(
                    path
                )
            )

    def sync_images_from_widget(
        self,
        *args,
    ):
        self.images = [
            self.image_list.item(index).data(
                Qt.ItemDataRole.UserRole
            )

            for index in range(
                self.image_list.count()
            )
        ]

    def update_image_view_mode(
        self,
        *args,
    ):
        mode = (
            self.image_view_mode
            .currentData()
        )


        if mode == "grid":
            self.image_list.setViewMode(
                QListView.ViewMode.IconMode
            )

            self.image_list.setIconSize(
                QSize(
                    128,
                    80,
                )
            )

            self.image_list.setGridSize(
                QSize(
                    165,
                    120,
                )
            )

            self.image_list.setResizeMode(
                QListView.ResizeMode.Adjust
            )

            self.image_list.setMovement(
                QListView.Movement.Snap
            )

            self.image_list.setWordWrap(
                True
            )

        else:
            self.image_list.setViewMode(
                QListView.ViewMode.ListMode
            )

            self.image_list.setIconSize(
                QSize(
                    64,
                    44,
                )
            )

            self.image_list.setGridSize(
                QSize()
            )

            self.image_list.setMovement(
                QListView.Movement.Snap
            )

            self.image_list.setWordWrap(
                False
            )

    def create_image_item(
        self,
        path,
    ):
        item = QListWidgetItem(
            Path(path).name
        )

        item.setData(
            Qt.ItemDataRole.UserRole,
            path,
        )

        item.setToolTip(
            path
        )


        pixmap = QPixmap(
            path
        )

        if not pixmap.isNull():
            thumbnail = pixmap.scaled(
                128,
                80,

                Qt.AspectRatioMode.KeepAspectRatio,

                Qt.TransformationMode.SmoothTransformation,
            )

            item.setIcon(
                QIcon(thumbnail)
            )


        return item

    # -----------------------------------------------------
    # IMAGES
    # -----------------------------------------------------

    def add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Adicionar imagens",
            "",
            (
                "Imagens "
                "(*.jpg *.jpeg *.png *.bmp *.webp)"
            ),
        )

        for file in files:
            if file not in self.images:
                self.images.append(
                    file
                )

                self.image_list.addItem(
                    self.create_image_item(
                        file
                    )
                )

    def remove_image(self):
        row = self.image_list.currentRow()

        if row < 0:
            return

        self.image_list.takeItem(
            row
        )

        self.sync_images_from_widget()

    # -----------------------------------------------------
    # TEXT
    # -----------------------------------------------------

    def insert_variable(self, item):
        text = item.text()

        variable = text.split(
            "  —  "
        )[0]

        cursor = (
            self.text_edit.textCursor()
        )

        cursor.insertText(
            variable
        )

        self.text_edit.setTextCursor(
            cursor
        )

        self.text_edit.setFocus()

    def apply_inline_bold(self):
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            return
        format = QTextCharFormat()
        format.setFontWeight(
            400 if cursor.charFormat().fontWeight() >= 600 else 700
        )
        cursor.mergeCharFormat(format)
        self.text_edit.setTextCursor(cursor)

    def apply_inline_italic(self):
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            return
        format = QTextCharFormat()
        format.setFontItalic(not cursor.charFormat().fontItalic())
        cursor.mergeCharFormat(format)
        self.text_edit.setTextCursor(cursor)

    def apply_inline_size(self):
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            return
        format = QTextCharFormat()
        format.setFontPointSize(self.inline_size.value())
        cursor.mergeCharFormat(format)
        self.text_edit.setTextCursor(cursor)

    def get_formatted_text(self):
        parts = []
        document = self.text_edit.document()
        for block_index in range(document.blockCount()):
            block = document.findBlockByNumber(block_index)
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                text = fragment.text()
                if not text:
                    iterator += 1
                    continue
                format = fragment.charFormat()
                if format.fontWeight() >= 600:
                    text = f"[b]{text}[/b]"
                if format.fontItalic():
                    text = f"[i]{text}[/i]"
                point_size = format.fontPointSize()
                if point_size and int(point_size) != self.text_size.value():
                    text = f"[size={int(point_size)}]{text}[/size]"
                parts.append(text)
                iterator += 1
            if block_index < document.blockCount() - 1:
                parts.append("\n")
        return "".join(parts)

    def set_formatted_text(self, markup):
        self.text_edit.clear()
        cursor = self.text_edit.textCursor()
        bold = False
        italic = False
        size = self.text_size.value()
        tokens = re.split(
            r"(\[/?b\]|\[/?i\]|\[size=\d+\]|\[/size\])",
            str(markup),
        )
        for token in tokens:
            if not token:
                continue
            if token == "[b]":
                bold = True
                continue
            if token == "[/b]":
                bold = False
                continue
            if token == "[i]":
                italic = True
                continue
            if token == "[/i]":
                italic = False
                continue
            if token.startswith("[size="):
                size = int(token[6:-1])
                continue
            if token == "[/size]":
                size = self.text_size.value()
                continue
            format = QTextCharFormat()
            format.setFontWeight(700 if bold else 400)
            format.setFontItalic(italic)
            format.setFontPointSize(size)
            cursor.insertText(token, format)
        self.text_edit.setTextCursor(cursor)

    def select_color(self):
        color = QColorDialog.getColor(
            QColor(
                self.text_color
            ),
            self,
        )

        if color.isValid():
            self.text_color = (
                color.name()
            )

            self.color_button.setText(
                self.text_color.upper()
            )
            self.color_preview.setStyleSheet(
                f"background-color: {self.text_color}; border: 1px solid #777;"
            )

    def select_shadow_color(self):
        color = QColorDialog.getColor(QColor(self.shadow_color), self)
        if color.isValid():
            self.shadow_color = color.name()
            self.shadow_color_button.setText(self.shadow_color.upper())

    def select_background_color(self):
        color = QColorDialog.getColor(QColor(self.background_color), self)
        if color.isValid():
            self.background_color = color.name()
            self.background_button.setText(self.background_color.upper())
            self.background_preview.setStyleSheet(
                f"background-color: {self.background_color}; border: 1px solid #777;"
            )

    # -----------------------------------------------------
    # CONFIG
    # -----------------------------------------------------

    def get_config(self):
        self.sync_images_from_widget()
        effects = []
        for index in range(self.effects_list.count()):
            item = self.effects_list.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                effects.append(item.data(Qt.ItemDataRole.UserRole))

        return {
            "images":
                self.images,

            "display_seconds":
                self.display_time.value(),

            "transition_seconds":
                self.transition_time.value(),

            "transition":
                self.transition.currentData(),

            "transition_effects":
                effects,

            "transition_random":
                self.random_effects.isChecked(),

            "image_fit":
                self.image_fit.currentData(),

            "text":
                self.get_formatted_text(),

            "text_enabled":
                self.text_enabled.isChecked(),

            "text_position":
                self.text_position.currentData(),

            "text_size":
                self.text_size.value(),

            "text_color":
                self.text_color,

            "text_margin":
                {
                    "top": self.margin_top.value(),
                    "right": self.margin_right.value(),
                    "bottom": self.margin_bottom.value(),
                    "left": self.margin_left.value(),
                },

            "text_shadow": {
                "enabled": self.shadow_enabled.isChecked(),
                "color": self.shadow_color,
                "offset_x": self.shadow_x.value(),
                "offset_y": self.shadow_y.value(),
                "opacity": self.shadow_opacity.value(),
            },

            "image_order":
                self.image_order.currentData(),

            "background_color":
                self.background_color,

            "exit_on_mouse":
                True,

            "mouse_threshold":
                15,
        }

    def write_config(
        self,
        path,
    ):
        config = self.get_config()

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                config,
                file,
                ensure_ascii=False,
                indent=4,
            )

    def update_window_title(self):
        if self.current_project_path:
            title = f"{Path(self.current_project_path).name} - OpenSCR"
        else:
            title = "OpenSCR"
        self.setWindowTitle(title)

    def get_recent_projects(self):
        settings = QSettings("bjmvictor", "OpenSCR")
        paths = settings.value(
            "recent_projects",
            [],
        )
        if isinstance(paths, str):
            paths = [paths]
        if not isinstance(paths, list):
            paths = []
        valid_paths = [path for path in paths if Path(path).exists()][:10]
        if valid_paths != paths:
            settings.setValue("recent_projects", valid_paths)
        return valid_paths

    def add_recent_project(self, path):
        path = str(Path(path).resolve())
        paths = [item for item in self.get_recent_projects() if item != path]
        paths.insert(0, path)
        QSettings("bjmvictor", "OpenSCR").setValue(
            "recent_projects",
            paths[:10],
        )
        self.update_recent_projects_menu()

    def clear_recent_projects(self):
        QSettings("bjmvictor", "OpenSCR").setValue("recent_projects", [])
        self.update_recent_projects_menu()

    def update_recent_projects_menu(self):
        if self.recent_menu is None:
            return
        self.recent_menu.clear()
        paths = self.get_recent_projects()
        if not paths:
            action = QAction("Nenhum projeto recente", self)
            action.setEnabled(False)
            self.recent_menu.addAction(action)
            return
        for path in paths:
            action = QAction(Path(path).name, self)
            action.setToolTip(path)
            action.triggered.connect(
                lambda checked=False, value=path: self.import_project(value)
            )
            self.recent_menu.addAction(action)
        self.recent_menu.addSeparator()
        clear_action = QAction("Limpar recentes", self)
        clear_action.triggered.connect(self.clear_recent_projects)
        self.recent_menu.addAction(clear_action)

    def export_project(self):
        self.save_project_as()

    def save_project(self):
        if self.current_project_path:
            self.write_config(self.current_project_path)
            self.add_recent_project(self.current_project_path)
        else:
            self.save_project_as()

    def save_project_as(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar projeto",
            "screensaver.json",
            "Projeto OpenSCR (*.json)",
        )
        if not filename:
            return
        if Path(filename).suffix.lower() != ".json":
            filename += ".json"
        self.write_config(filename)
        self.current_project_path = str(Path(filename).resolve())
        self.add_recent_project(self.current_project_path)
        self.update_window_title()

    def import_project(self, filename=None):
        if filename is None:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                "Abrir projeto",
                "",
                "Projeto OpenSCR (*.json)",
            )
        if not filename:
            return False

        try:
            with open(filename, "r", encoding="utf-8") as file:
                config = json.load(file)
            base_dir = Path(filename).resolve().parent
            self.images = [
                str((base_dir / image).resolve())
                if not Path(image).is_absolute() else image
                for image in config.get("images", [])
            ]
            self.image_list.clear()
            self.refresh_image_list()
            self.apply_config(config)
            self.current_project_path = str(Path(filename).resolve())
            self.add_recent_project(self.current_project_path)
            self.update_window_title()
            return True
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "OpenSCR",
                f"Não foi possível importar o projeto.\n\n{exc}",
            )
            return False

    def apply_config(self, config):
        self.display_time.setValue(config.get("display_seconds", 8))
        self.transition_time.setValue(config.get("transition_seconds", 1.5))
        self.set_combo_data(self.transition, config.get("transition", "random"))
        self.set_combo_data(self.image_fit, config.get("image_fit", "cover"))
        self.text_enabled.setChecked(config.get("text_enabled", True))
        self.set_combo_data(self.text_position, config.get("text_position", "bottom_right"))
        self.text_size.setValue(config.get("text_size", 32))
        self.set_formatted_text(config.get("text", ""))
        self.set_combo_data(
            self.image_order,
            config.get(
                "image_order",
                "forward",
            ),
        )

        self.text_color = config.get("text_color", "#FFFFFF")
        self.color_button.setText(self.text_color.upper())
        self.color_preview.setStyleSheet(
            f"background-color: {self.text_color}; border: 1px solid #777;"
        )

        margins = config.get("text_margin", 50)
        if isinstance(margins, int):
            margins = {key: margins for key in ("top", "right", "bottom", "left")}
        for key, control in (
            ("top", self.margin_top),
            ("right", self.margin_right),
            ("bottom", self.margin_bottom),
            ("left", self.margin_left),
        ):
            control.setValue(margins.get(key, 50))

        shadow = config.get("text_shadow", {})
        self.shadow_enabled.setChecked(shadow.get("enabled", True))
        self.shadow_color = shadow.get("color", "#000000")
        self.shadow_color_button.setText(self.shadow_color.upper())
        self.shadow_x.setValue(shadow.get("offset_x", 2))
        self.shadow_y.setValue(shadow.get("offset_y", 2))
        self.shadow_opacity.setValue(shadow.get("opacity", 180))

        self.background_color = config.get("background_color", "#000000")
        self.background_button.setText(self.background_color.upper())
        self.background_preview.setStyleSheet(
            f"background-color: {self.background_color}; border: 1px solid #777;"
        )

        configured_effects = config.get(
            "transition_effects",
            [
                "fade",
                "gradient",
                "slide_left",
                "slide_right",
                "zoom",
                "slide_up",
                "slide_down",
            ],
        )
        for index in range(self.effects_list.count()):
            item = self.effects_list.item(index)
            item.setCheckState(
                Qt.CheckState.Checked
                if item.data(Qt.ItemDataRole.UserRole) in configured_effects
                else Qt.CheckState.Unchecked
            )
        self.random_effects.setChecked(config.get("transition_random", False))

    @staticmethod
    def set_combo_data(combo, value):
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    # -----------------------------------------------------
    # PREVIEW
    # -----------------------------------------------------

    def preview(self):
        if not self.images:
            QMessageBox.warning(
                self,
                "OpenSCR",
                "Adicione pelo menos uma imagem.",
            )
            return


        preview_dir = (
            Path(
                tempfile.gettempdir()
            )
            /
            "OpenSCR"
        )


        preview_dir.mkdir(
            parents=True,
            exist_ok=True,
        )


        preview_path = (
            preview_dir
            /
            "OpenSCRPreview.scr"
        )

        self.set_busy(True)
        QApplication.processEvents()


        try:
            build_screensaver(
                self.get_config(),
                preview_path,
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "OpenSCR",
                (
                    "Não foi possível gerar "
                    "o preview.\n\n"
                    f"{exc}"
                ),
            )
            self.set_busy(False)
            return


        if (
            self.preview_process is not None
            and
            self.preview_process.state()
            !=
            QProcess.ProcessState.NotRunning
        ):
            self.preview_process.kill()

            self.preview_process.waitForFinished(
                2000
            )


        self.preview_output = ""


        self.preview_process = QProcess(
            self
        )


        self.preview_process.setProgram(
            str(
                preview_path
            )
        )


        self.preview_process.setArguments(
            [
                "/s"
            ]
        )


        self.preview_process.errorOccurred.connect(
            self.on_preview_process_error
        )

        self.preview_process.readyReadStandardOutput.connect(
            self.on_preview_output
        )


        self.preview_process.finished.connect(
            self.on_preview_finished
        )


        self.statusBar().showMessage(
            "Abrindo preview..."
        )

        self.preview_process.start()

    def on_preview_output(self):
        if not self.preview_process:
            return

        data = (
            self.preview_process
            .readAllStandardOutput()
            .data()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        self.preview_output += data

        if data:
            print(
                "[OpenSCR Preview]"
            )
            print(data)


    def on_preview_process_error(
        self,
        error,
    ):
        if not self.preview_process:
            return

        message = (
            self.preview_process
            .errorString()
        )

        QMessageBox.critical(
            self,
            "OpenSCR - Erro no preview",
            (
                "Não foi possível iniciar "
                "o preview.\n\n"
                f"{message}"
            ),
        )

        self.statusBar().showMessage(
            "Falha ao abrir preview.",
            5000,
        )
        self.set_busy(False)


    def on_preview_finished(
        self,
        exit_code,
        exit_status,
    ):
        # 0 = usuário fechou normalmente
        if exit_code == 0:
            self.statusBar().showMessage(
                "Preview encerrado.",
                3000,
            )
            self.set_busy(False)
            return

        message = (
            "O preview foi encerrado "
            f"com código {exit_code}."
        )

        if self.preview_output.strip():
            message += (
                "\n\nSaída do runtime:\n\n"
                + self.preview_output[-4000:]
            )

        QMessageBox.critical(
            self,
            "OpenSCR - Falha no preview",
            message,
        )

        self.statusBar().showMessage(
            "Erro no preview.",
            5000,
        )
        self.set_busy(False)

    # -----------------------------------------------------
    # BUILD
    # -----------------------------------------------------

    def build_scr(self):
        if not self.images:
            QMessageBox.warning(
                self,
                "OpenSCR",
                "Adicione pelo menos uma imagem.",
            )

            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Gerar protetor de tela",
            "MeuProtetor.scr",
            "Screen Saver (*.scr)",
        )

        if not filename:
            return

        self.set_busy(True)
        QApplication.processEvents()

        self.build_button.setText(
            "Gerando..."
        )

        self.statusBar().showMessage(
            "Gerando protetor de tela..."
        )

        self.build_thread = ScrBuildThread(
            self.get_config(),
            filename,
            self,
        )

        self.build_thread.succeeded.connect(
            self.on_build_success
        )

        self.build_thread.failed.connect(
            self.on_build_error
        )

        self.build_thread.finished.connect(
            self.on_build_finished
        )

        self.build_thread.start()

    def on_build_success(
        self,
        scr_path,
    ):
        QMessageBox.information(
            self,
            "OpenSCR",
            (
                "Protetor de tela criado "
                "com sucesso.\n\n"
                f"{scr_path}\n\n"
                "O arquivo .SCR foi gerado"
                "e salvo."
            ),
        )


        self.statusBar().showMessage(
            (
                "Protetor de tela criado "
                "com sucesso."
            ),
            5000,
        )


    def on_build_error(
        self,
        message,
    ):
        QMessageBox.critical(
            self,
            "OpenSCR",
            message,
        )


    def on_build_finished(self):
        self.set_busy(False)

        self.build_button.setText(
            "Gerar .SCR"
        )

        self.statusBar().showMessage(
            "Pronto",
            3000,
        )

        if self.build_thread:
            self.build_thread.deleteLater()

        self.build_thread = None

    def set_busy(self, busy):
        self.setEnabled(not busy)
        self.preview_button.setEnabled(not busy)
        self.build_button.setEnabled(not busy)
        self.loading_label.setVisible(busy)
        if busy:
            self.loading_index = 0
            self.update_loading_indicator()
            self.loading_timer.start(120)
        else:
            self.loading_timer.stop()
            self.loading_label.clear()

    def update_loading_indicator(self):
        frames = ["|", "/", "-", "\\"]
        frame = frames[self.loading_index % len(frames)]
        self.loading_label.setText(f"{frame} Carregando...")
        self.loading_index += 1

def main():
    configure_windows_app_id()

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        "OpenSCR"
    )

    app.setApplicationDisplayName(
        "OpenSCR"
    )

    app.setOrganizationName(
        "bjmvictor"
    )

    icon_path = resource_path(
        "assets/OpenSCR.ico"
    )

    splash_path = resource_path(
        "assets/splash.png"
    )

    if icon_path.exists():
        app.setWindowIcon(
            QIcon(str(icon_path))
        )

    splash = None
    if splash_path.exists() and not getattr(sys, "frozen", False):
        splash_pixmap = QPixmap(str(splash_path)).scaled(
            600,
            600,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        splash = QSplashScreen(splash_pixmap)
        splash.showMessage(
            "Carregando OpenSCR...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            Qt.GlobalColor.white,
        )
        splash.show()
        app.processEvents()

    window = OpenSCRCreator()

    window.show()

    if splash:
        splash.finish(window)

    if getattr(sys, "frozen", False):
        def close_native_splash():
            try:
                splash_module = importlib.import_module("pyi_splash")
                splash_module.close()
            except (ImportError, AttributeError):
                pass

        app.processEvents()
        QTimer.singleShot(150, close_native_splash)

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()