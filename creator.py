import json
import os
import subprocess
import sys
from build_worker import (
    ScrBuildThread,
)
from pathlib import Path
from PySide6.QtCore import (
    Qt,
    QProcess,
)
from PySide6.QtGui import (
    QColor,
    QIcon,
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
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from runtime.variables import (
    AVAILABLE_VARIABLES,
)


class OpenSCRCreator(
    QMainWindow
):
    def __init__(self):
        super().__init__()
        self.build_thread = None
        self.preview_process = None
        self.preview_output = ""

        self.images = []

        self.text_color = (
            "#FFFFFF"
        )

        self.setWindowTitle(
            "OpenSCR"
        )

        icon_path = (
            Path(__file__).resolve().parent
            / "assets"
            / "OpenSCR.ico"
        )

        if icon_path.exists():
            self.setWindowIcon(
                QIcon(
                    str(icon_path)
                )
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
        central = QWidget()

        self.setCentralWidget(
            central
        )

        main_layout = QVBoxLayout(
            central
        )

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

        main_layout.addWidget(
            title
        )

        main_layout.addWidget(
            subtitle
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
            [600, 400]
        )

        buttons = QHBoxLayout()

        self.preview_button = QPushButton(
            "▶ Visualizar"
        )

        self.save_button = QPushButton(
            "Salvar projeto"
        )

        self.build_button = QPushButton(
            "Gerar .SCR"
        )

        self.preview_button.clicked.connect(
            self.preview
        )

        self.save_button.clicked.connect(
            self.save_project
        )

        self.build_button.clicked.connect(
            self.build_scr
        )

        buttons.addStretch()

        buttons.addWidget(
            self.preview_button
        )

        buttons.addWidget(
            self.save_button
        )

        buttons.addWidget(
            self.build_button
        )

        main_layout.addLayout(
            buttons
        )

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

        image_buttons = QHBoxLayout()

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

        return panel

    # -----------------------------------------------------
    # RIGHT PANEL
    # -----------------------------------------------------

    def create_right_panel(self):
        panel = QWidget()

        layout = QVBoxLayout(
            panel
        )

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
            self.color_button,
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

        return panel

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
                    file
                )

    def remove_image(self):
        row = (
            self.image_list.currentRow()
        )

        if row < 0:
            return

        self.image_list.takeItem(
            row
        )

        del self.images[row]

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

    # -----------------------------------------------------
    # CONFIG
    # -----------------------------------------------------

    def get_config(self):
        return {
            "images":
                self.images,

            "display_seconds":
                self.display_time.value(),

            "transition_seconds":
                self.transition_time.value(),

            "transition":
                self.transition.currentData(),

            "image_fit":
                self.image_fit.currentData(),

            "text":
                self.text_edit.toPlainText(),

            "text_enabled":
                self.text_enabled.isChecked(),

            "text_position":
                self.text_position.currentData(),

            "text_size":
                self.text_size.value(),

            "text_color":
                self.text_color,

            "text_margin":
                50,

            "background_color":
                "#000000",

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

        project_dir = Path(
            __file__
        ).resolve().parent

        config_path = (
            project_dir
            / "preview_config.json"
        )

        self.write_config(
            str(config_path)
        )

        # Evita iniciar dois previews simultaneamente
        if (
            self.preview_process is not None
            and self.preview_process.state()
            != QProcess.ProcessState.NotRunning
        ):
            self.preview_process.kill()
            self.preview_process.waitForFinished(
                2000
            )

        self.preview_output = ""

        self.preview_process = QProcess(
            self
        )

        self.preview_process.setWorkingDirectory(
            str(project_dir)
        )

        self.preview_process.setProcessChannelMode(
            QProcess.ProcessChannelMode.MergedChannels
        )

        self.preview_process.readyReadStandardOutput.connect(
            self.on_preview_output
        )

        self.preview_process.errorOccurred.connect(
            self.on_preview_process_error
        )

        self.preview_process.finished.connect(
            self.on_preview_finished
        )

        self.statusBar().showMessage(
            "Abrindo preview..."
        )

        if getattr(
            sys,
            "frozen",
            False,
        ):
            base_path = Path(
                sys._MEIPASS
            )

            runtime_path = (
                base_path
                / "resources"
                / "OpenSCRRuntime.exe"
            )

            if not runtime_path.exists():
                QMessageBox.critical(
                    self,
                    "OpenSCR",
                    (
                        "O runtime de preview "
                        "não foi encontrado.\n\n"
                        f"{runtime_path}"
                    ),
                )
                return

            self.preview_process.start(
                str(runtime_path),
                [
                    "--config",
                    str(config_path),
                    "/s",
                ],
            )

        else:
            self.preview_process.start(
                sys.executable,
                [
                    "-m",
                    "runtime.app",
                    "--config",
                    str(config_path),
                    "/s",
                ],
            )

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
            return

        log_path = (
            Path(
                os.environ.get(
                    "LOCALAPPDATA",
                    "",
                )
            )
            / "OpenSCR"
            / "logs"
            / "screensaver.log"
        )

        message = (
            "O preview foi encerrado "
            f"com código {exit_code}."
        )

        if self.preview_output.strip():
            message += (
                "\n\nSaída do runtime:\n\n"
                + self.preview_output[-4000:]
            )

        if log_path.exists():
            message += (
                "\n\nO log completo está em:\n"
                f"{log_path}"
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

    # -----------------------------------------------------
    # SAVE PROJECT
    # -----------------------------------------------------

    def save_project(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar projeto",
            "screensaver.json",
            "Projeto OpenSCR (*.json)",
        )

        if not filename:
            return

        self.write_config(
            filename
        )

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

        self.build_button.setEnabled(
            False
        )

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
        data_path,
    ):
        QMessageBox.information(
            self,
            "OpenSCR",
            (
                "Protetor de tela criado "
                "com sucesso.\n\n"
                f"{scr_path}\n\n"
                "Os dados do protetor estão em:\n"
                f"{data_path}"
            ),
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
        self.build_button.setEnabled(
            True
        )

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

def main():
    app = QApplication(
        sys.argv
    )

    window = OpenSCRCreator()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()