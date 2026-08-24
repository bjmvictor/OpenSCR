import ctypes
import importlib
import json
import re
import sys
import tempfile

if sys.version_info[:2] != (3, 10):
    raise SystemExit(
        "OpenSCR development requires Python 3.10. "
        f"The current interpreter is Python {sys.version_info.major}."
        f"{sys.version_info.minor}. Recreate .venv with Python 3.10."
    )

from builder import (
    build_screensaver,
)
from build_worker import (
    ScrBuildThread,
)
from pathlib import Path
from PySide2.QtCore import (
    Qt, QProcess, QSize, QSettings, QTimer, QTranslator, QLibraryInfo,
)
from PySide2.QtGui import QColor, QIcon, QPixmap, QTextCharFormat
from PySide2.QtWidgets import (
    QAction, QApplication, QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox,
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QSpinBox,
    QSplitter, QSplashScreen, QTextEdit, QVBoxLayout, QWidget,
    QAbstractItemView, QListView, QSizePolicy, QScrollArea,
)

from openscr_variables import (
    AVAILABLE_VARIABLES,
)

APP_VERSION = "2.0.5"
PROJECT_URL = "https://github.com/bjmvictor/OpenSCR"
TEXT_PLACEHOLDER = (
    "Digite seu texto aqui...\n\n"
    "Exemplo:\n"
    "Hoje é {weekday}, {date}\n"
    "{time_seconds}"
)


def load_translations(language):
    path = resource_path(f"locales/{language}.json")
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}

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
        self.preview_started = False
        self.preview_output = ""
        self.preview_started = False
        self.current_project_path = None
        self.saved_project_state = None
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
        self.load_preferences()
        self.saved_project_state = self.project_state()

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
            Qt.Horizontal
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

        view_menu = self.menuBar().addMenu("Exibir")
        theme_menu = view_menu.addMenu("Tema")
        for label, value in (("Sistema", "system"), ("Claro", "light"), ("Escuro", "dark")):
            action = QAction(label, self)
            action.triggered.connect(lambda checked=False, selected=value: self.set_theme(selected))
            theme_menu.addAction(action)

        language_menu = view_menu.addMenu("Idioma")
        for label, value in (
            ("Português (Brasil)", "pt_BR"), ("English", "en"),
            ("Español", "es"), ("Français", "fr"),
            ("中文", "zh_CN"), ("日本語", "ja"),
        ):
            action = QAction(label, self)
            action.triggered.connect(lambda checked=False, selected=value: self.set_language(selected))
            language_menu.addAction(action)

        help_menu = self.menuBar().addMenu("Sobre")
        about_action = QAction("Sobre o OpenSCR", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def load_preferences(self):
        settings = QSettings("bjmvictor", "OpenSCR")
        self.set_theme(settings.value("theme", "system"))
        self.set_language(settings.value("language", "pt_BR"), persist=False)

    def set_theme(self, theme):
        theme = theme if theme in ("system", "light", "dark") else "system"
        styles = {
            "system": "",
            "light": """
                QWidget { background: #f7f7f8; color: #202124; }
                QTextEdit, QListWidget, QComboBox, QSpinBox, QDoubleSpinBox {
                    background: #ffffff; color: #202124;
                    border: 1px solid #c7c9cc; border-radius: 4px;
                }
                QPushButton {
                    background: #ffffff; color: #202124;
                    border: 1px solid #c7c9cc; border-radius: 5px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background: #e8f0fe; color: #174ea6;
                    border-color: #5f87d8;
                }
                QPushButton:pressed, QPushButton:checked {
                    background: #d2e3fc; color: #174ea6;
                    border-color: #3f6fbd;
                }
                QPushButton:focus { border: 2px solid #5f87d8; }
                QPushButton:disabled {
                    background: #eeeeef; color: #9aa0a6;
                    border-color: #dadce0;
                }
                QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
                QTextEdit:hover, QListWidget:hover { border-color: #5f87d8; }
                QListWidget::item:hover { background: #e8f0fe; }
                QListWidget::item:selected { background: #d2e3fc; color: #174ea6; }
                QMenuBar::item:selected, QMenu::item:selected { background: #e8f0fe; }
            """,
            "dark": """
                QWidget { background: #202124; color: #f1f3f4; }
                QTextEdit, QListWidget, QComboBox, QSpinBox, QDoubleSpinBox {
                    background: #303134; color: #f1f3f4;
                    border: 1px solid #5f6368; border-radius: 4px;
                }
                QPushButton {
                    background: #3c4043; color: #f1f3f4;
                    border: 1px solid #5f6368; border-radius: 5px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background: #4c5f7a; color: #ffffff;
                    border-color: #8ab4f8;
                }
                QPushButton:pressed, QPushButton:checked {
                    background: #314968; color: #aecbfa;
                    border-color: #aecbfa;
                }
                QPushButton:focus { border: 2px solid #8ab4f8; }
                QPushButton:disabled {
                    background: #292a2d; color: #70757a;
                    border-color: #3c4043;
                }
                QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
                QTextEdit:hover, QListWidget:hover { border-color: #8ab4f8; }
                QListWidget::item:hover { background: #3c4b63; }
                QListWidget::item:selected { background: #314968; color: #ffffff; }
                QMenuBar::item:selected, QMenu::item:selected { background: #3c4b63; }
            """,
        }
        QApplication.instance().setStyleSheet(styles[theme])
        QSettings("bjmvictor", "OpenSCR").setValue("theme", theme)

    def set_language(self, language, persist=True):
        supported = ("pt_BR", "en", "es", "fr", "zh_CN", "ja")
        language = language if language in supported else "pt_BR"
        if persist:
            QSettings("bjmvictor", "OpenSCR").setValue("language", language)
        previous = getattr(self, "translations", {})
        translations = load_translations(language)
        normalize = {value: key for key, value in previous.items()}
        self._apply_translation(normalize)
        self.translations = translations
        self.language = language
        self._apply_translation(translations)
        if hasattr(self, "text_edit"):
            self.text_edit.setPlaceholderText(self.translate(TEXT_PLACEHOLDER))
        self.refresh_variables_list()
        self._install_qt_translator(language)

    def _apply_translation(self, lookup):
        for widget in self.findChildren(QWidget):
            if isinstance(widget, (QLabel, QPushButton, QCheckBox)) and widget.text() in lookup:
                widget.setText(lookup[widget.text()])
        for group in self.findChildren(QGroupBox):
            if group.title() in lookup:
                group.setTitle(lookup[group.title()])
        for action in self.findChildren(QAction):
            if action.text() in lookup:
                action.setText(lookup[action.text()])
        for combo in self.findChildren(QComboBox):
            for index in range(combo.count()):
                if combo.itemText(index) in lookup:
                    combo.setItemText(index, lookup[combo.itemText(index)])
        effects_list = getattr(self, "effects_list", None)
        if effects_list is not None:
            for index in range(effects_list.count()):
                item = effects_list.item(index)
                if item.text() in lookup:
                    item.setText(lookup[item.text()])

    def _install_qt_translator(self, language):
        app = QApplication.instance()
        previous = getattr(app, "openscr_qt_translator", None)
        if previous is not None:
            app.removeTranslator(previous)
        translator = QTranslator(app)
        translations_path = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
        if translator.load(f"qtbase_{language}", translations_path):
            app.installTranslator(translator)
            app.openscr_qt_translator = translator
        else:
            app.openscr_qt_translator = None

    def translate(self, source):
        return getattr(self, "translations", {}).get(source, source)

    def show_about(self):
        box = QMessageBox(self)
        box.setWindowTitle(self.translate("Sobre o OpenSCR"))
        box.setIconPixmap(self.windowIcon().pixmap(64, 64))
        box.setText(f"<h3>OpenSCR {APP_VERSION}</h3>")
        box.setInformativeText(
            f"{self.translate('Open Source Windows Screensaver Creator')}<br><br>"
            f"{self.translate('Desenvolvido por')} <b>Benjamin Victor</b><br>"
            f'<a href="{PROJECT_URL}">{PROJECT_URL}</a><br><br>'
            f"{self.translate('Licença MIT · Python, PySide2/Qt 5 e runtime nativo Win32')}"
        )
        box.setTextFormat(Qt.RichText)
        (box.exec if hasattr(box, "exec") else box.exec_)()

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
            QAbstractItemView.InternalMove
        )

        self.image_list.setDefaultDropAction(
            Qt.MoveAction
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
        # addItem() selects the first option before the signal is connected,
        # so apply the list dimensions explicitly on first creation.
        self.update_image_view_mode()

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

        image_buttons.addWidget(
            add_image
        )

        image_buttons.addWidget(
            remove_image
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
        self.transition.addItem("Pixel", "pixel")
        self.transition.addItem("Dissolver", "dissolve")
        self.transition.addItem("Glitch", "glitch")
        self.transition.addItem("Persianas", "blinds")

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
            ("Pixel", "pixel"),
            ("Dissolver", "dissolve"),
            ("Glitch", "glitch"),
            ("Persianas", "blinds"),
        ):
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, value)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
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
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        self.text_edit.setPlaceholderText(TEXT_PLACEHOLDER)

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
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)

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

        # Retained in project data as the fallback for unformatted text, but
        # edited text sizes are now controlled exclusively by the format bar.
        self.default_text_size = 32

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

        self.refresh_variables_list()

        self.variables_list.itemDoubleClicked.connect(
            self.insert_variable
        )

        variables_layout.addWidget(
            self.variables_list
        )

        layout.addWidget(
            variables_group
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setMinimumWidth(300)
        return scroll

    def refresh_variables_list(self):
        variables_list = getattr(self, "variables_list", None)
        if variables_list is None:
            return
        variables_list.clear()
        for variable, description in AVAILABLE_VARIABLES.items():
            variables_list.addItem(
                f"{variable}  —  {self.translate(description)}"
            )

    def create_shadow_offset_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(self.shadow_x)
        layout.addWidget(QLabel("/"))
        layout.addWidget(self.shadow_y)
        return layout

    def set_effects_checked(self, checked):
        for index in range(self.effects_list.count()):
            self.effects_list.item(index).setCheckState(
                Qt.Checked
                if checked else Qt.Unchecked
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
                Qt.UserRole
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
                QListView.IconMode
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
                QListView.Adjust
            )

            self.image_list.setMovement(
                QListView.Snap
            )

            self.image_list.setWordWrap(
                True
            )

        else:
            self.image_list.setViewMode(
                QListView.ListMode
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
                QListView.Snap
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
            Qt.UserRole,
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

                Qt.KeepAspectRatio,

                Qt.SmoothTransformation,
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
            self.translate("Adicionar imagens"),
            "",
            self.translate("Imagens (*.jpg *.jpeg *.png *.bmp *.webp)"),
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
                if point_size and int(point_size) != self.default_text_size:
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
        size = self.default_text_size
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
                size = self.default_text_size
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
            if item.checkState() == Qt.Checked:
                effects.append(item.data(Qt.UserRole))

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
                self.default_text_size,

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

    def project_state(self):
        """Return a stable representation used to detect unsaved changes."""
        return json.dumps(self.get_config(), ensure_ascii=False, sort_keys=True)

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
            action = QAction(self.translate("Nenhum projeto recente"), self)
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
        clear_action = QAction(self.translate("Limpar recentes"), self)
        clear_action.triggered.connect(self.clear_recent_projects)
        self.recent_menu.addAction(clear_action)

    def export_project(self):
        self.save_project_as()

    def save_project(self):
        if self.current_project_path:
            try:
                self.write_config(self.current_project_path)
                self.add_recent_project(self.current_project_path)
                self.saved_project_state = self.project_state()
                return True
            except OSError as exc:
                QMessageBox.critical(self, "OpenSCR", f"{self.translate('Não foi possível salvar o projeto.')}\n\n{exc}")
                return False
        return self.save_project_as()

    def save_project_as(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.translate("Salvar projeto"),
            "screensaver.json",
            self.translate("Projeto OpenSCR (*.json)"),
        )
        if not filename:
            return False
        if Path(filename).suffix.lower() != ".json":
            filename += ".json"
        try:
            self.write_config(filename)
        except OSError as exc:
            QMessageBox.critical(self, "OpenSCR", f"{self.translate('Não foi possível salvar o projeto.')}\n\n{exc}")
            return False
        self.current_project_path = str(Path(filename).resolve())
        self.add_recent_project(self.current_project_path)
        self.update_window_title()
        self.saved_project_state = self.project_state()
        return True

    def import_project(self, filename=None):
        if filename is None:
            filename, _ = QFileDialog.getOpenFileName(
                self,
                self.translate("Abrir projeto"),
                "",
                self.translate("Projeto OpenSCR (*.json)"),
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
            self.saved_project_state = self.project_state()
            return True
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "OpenSCR",
                f"{self.translate('Não foi possível importar o projeto.')}\n\n{exc}",
            )
            return False

    def closeEvent(self, event):
        if self.saved_project_state == self.project_state():
            event.accept()
            return
        box = QMessageBox(QMessageBox.Question, "OpenSCR",
            self.translate("O projeto foi alterado. Deseja salvar antes de fechar?"),
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, self)
        box.setDefaultButton(QMessageBox.Save)
        for button, key in ((QMessageBox.Save, "Save"), (QMessageBox.Discard, "Discard"), (QMessageBox.Cancel, "Cancel")):
            box.button(button).setText(self.translate(key))
        answer = (box.exec if hasattr(box, "exec") else box.exec_)()
        if answer == QMessageBox.Save:
            event.accept() if self.save_project() else event.ignore()
        elif answer == QMessageBox.Discard:
            event.accept()
        else:
            event.ignore()

    def apply_config(self, config):
        self.display_time.setValue(config.get("display_seconds", 8))
        self.transition_time.setValue(config.get("transition_seconds", 1.5))
        self.set_combo_data(self.transition, config.get("transition", "random"))
        self.set_combo_data(self.image_fit, config.get("image_fit", "cover"))
        self.text_enabled.setChecked(config.get("text_enabled", True))
        self.set_combo_data(self.text_position, config.get("text_position", "bottom_right"))
        self.default_text_size = int(config.get("text_size", 32))
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
                "pixel",
                "dissolve",
                "glitch",
                "blinds",
            ],
        )
        for index in range(self.effects_list.count()):
            item = self.effects_list.item(index)
            item.setCheckState(
                Qt.Checked
                if item.data(Qt.UserRole) in configured_effects
                else Qt.Unchecked
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
                self.translate("Adicione pelo menos uma imagem."),
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
                    self.translate("Não foi possível gerar o preview.")
                    + "\n\n"
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
            QProcess.NotRunning
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
        self.preview_process.started.connect(
            lambda: setattr(self, "preview_started", True)
        )

        self.preview_process.readyReadStandardOutput.connect(
            self.on_preview_output
        )


        self.preview_process.finished.connect(
            self.on_preview_finished
        )


        self.statusBar().showMessage(
            self.translate("Abrindo preview...")
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

        if error == QProcess.Crashed and self.preview_started:
            # Screen savers close themselves in response to user input. Some
            # Windows/Qt 5 combinations report that normal native exit as
            # QProcess.Crashed even though preview completed successfully.
            self.statusBar().showMessage(self.translate("Preview encerrado."), 3000)
            self.set_busy(False)
            return

        message = (
            self.preview_process
            .errorString()
        )

        QMessageBox.critical(
            self,
            self.translate("OpenSCR - Erro no preview"),
            (
                self.translate("Não foi possível iniciar o preview.")
                + "\n\n"
                f"{message}"
            ),
        )

        self.statusBar().showMessage(
            self.translate("Falha ao abrir preview."),
            5000,
        )
        self.set_busy(False)


    def on_preview_finished(
        self,
        exit_code,
        exit_status,
    ):
        # A preview that reached the running state and was closed by keyboard,
        # click, or mouse movement is a successful preview session.
        if exit_code == 0 or self.preview_started:
            self.statusBar().showMessage(
                self.translate("Preview encerrado."),
                3000,
            )
            self.set_busy(False)
            self.preview_started = False
            return

        message = (
            self.translate("O preview foi encerrado com código {code}.").format(
                code=exit_code
            )
        )

        if self.preview_output.strip():
            message += (
                f"\n\n{self.translate('Saída do runtime:')}\n\n"
                + self.preview_output[-4000:]
            )

        QMessageBox.critical(
            self,
            self.translate("OpenSCR - Falha no preview"),
            message,
        )

        self.statusBar().showMessage(
            self.translate("Erro no preview."),
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
                self.translate("Adicione pelo menos uma imagem."),
            )

            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            self.translate("Gerar protetor de tela"),
            "MeuProtetor.scr",
            self.translate("Protetor de tela (*.scr)"),
        )

        if not filename:
            return

        self.set_busy(True)
        QApplication.processEvents()

        self.build_button.setText(
            self.translate("Gerando...")
        )

        self.statusBar().showMessage(
            self.translate("Gerando protetor de tela...")
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
                self.translate("Protetor de tela criado com sucesso.")
                + "\n\n"
                f"{scr_path}\n\n"
                + self.translate("O arquivo .SCR foi gerado e salvo.")
            ),
        )


        self.statusBar().showMessage(
            (
                self.translate("Protetor de tela criado com sucesso.")
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
            self.translate("Gerar .SCR")
        )

        self.statusBar().showMessage(
            self.translate("Pronto"),
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
        self.loading_label.setText(f"{frame} {self.translate('Carregando...')}")
        self.loading_index += 1

def main():
    configure_windows_app_id()

    QApplication.setAttribute(Qt.AA_DontUseNativeDialogs, True)

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
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        splash = QSplashScreen(splash_pixmap)
        language = QSettings("bjmvictor", "OpenSCR").value("language", "pt_BR")
        splash_text = load_translations(language).get(
            "Carregando OpenSCR...", "Carregando OpenSCR..."
        )
        splash.showMessage(
            splash_text,
            Qt.AlignBottom | Qt.AlignHCenter,
            Qt.white,
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
        (app.exec if hasattr(app, "exec") else app.exec_)()
    )


if __name__ == "__main__":
    main()
