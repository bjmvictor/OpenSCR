
from PySide6.QtCore import (
    QThread,
    Signal,
)

from builder import (
    build_screensaver,
)


class ScrBuildThread(QThread):
    succeeded = Signal(
        str,
        str,
    )

    failed = Signal(
        str,
    )

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
            scr, data_dir = (
                build_screensaver(
                    self.config,
                    self.destination,
                )
            )

            self.succeeded.emit(
                str(scr),
                str(data_dir),
            )

        except Exception as exc:
            self.failed.emit(
                str(exc)
            )