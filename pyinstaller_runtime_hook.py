"""Prepare native DLL search paths before PySide2 is imported.

PyInstaller stores the PySide2 and shiboken DLLs in separate directories. Some
Windows loader configurations do not resolve that dependency chain from the
extension module directory alone.
"""

import os
import sys
from pathlib import Path


_dll_directory_handles = []

if sys.platform == "win32" and getattr(sys, "frozen", False):
    bundle_root = Path(sys._MEIPASS)
    dll_directories = (
        bundle_root,
        bundle_root / "PySide2",
        bundle_root / "shiboken2",
    )

    existing = [str(path) for path in dll_directories if path.is_dir()]
    os.environ["PATH"] = os.pathsep.join(existing + [os.environ.get("PATH", "")])

    add_dll_directory = getattr(os, "add_dll_directory", None)
    if add_dll_directory is not None:
        # Handles must remain alive for as long as native Qt modules are used.
        for directory in existing:
            _dll_directory_handles.append(add_dll_directory(directory))
