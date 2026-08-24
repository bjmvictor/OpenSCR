from PySide2.QtCore import QThread, Signal

from builder import (
    build_screensaver,
)


class ScrBuildThread(QThread):
    succeeded = Signal(str)

    failed = Signal(str)


    def __init__(
        self,
        config,
        destination,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self.config = config

        self.destination = destination


    def run(self):
        try:
            scr_path = (
                build_screensaver(
                    self.config,
                    self.destination,
                )
            )


            self.succeeded.emit(
                str(scr_path)
            )

        except Exception as exc:
            self.failed.emit(
                str(exc)
            )
