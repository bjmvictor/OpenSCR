# OpenSCR

OpenSCR is an open-source desktop application for creating self-contained
Windows screen savers from images, formatted text, dynamic variables, and
transitions.

## Main features

- Image slideshows with multiple ordering and fit modes.
- Text with dynamic date, time, computer, and user variables.
- Multi-monitor preview and native Windows `.scr` generation.
- Fade, zoom, slide, pixel, dissolve, glitch, blinds, and other effects.
- Project files, recent files, themes, and save-before-close protection.
- Interface in Portuguese, English, Spanish, French, Chinese, and Japanese.

## Installation

Download the x64 Setup package from GitHub Releases. The installer includes the
application and installs or repairs the Microsoft Visual C++ Runtime required
by Qt.

The same installer supports Windows Server 2016 build 14393, Windows 10,
Windows 11, and newer x64 Windows Server versions. Windows 32-bit is not
supported.

## Development

OpenSCR uses Python 3.10 and PySide2/Qt 5 as its Windows compatibility baseline.
PySide2 does not provide Windows packages for Python 3.11 or newer.

First install 64-bit Python 3.10. On Windows, it can be installed with:

```powershell
winget install --exact --id Python.Python.3.10
```

Close and reopen PowerShell after installation. Create the environment by
explicitly selecting Python 3.10; do not use an unqualified `python` or `py`
command because it may select another installed version.

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python creator.py
```

Confirm that `python --version` reports `Python 3.10.x` after activation. If
the launcher cannot find 3.10, use the full path shown by
`Get-Command python3.10` or by the Python installer.

To build the application and installer:

```powershell
python build_native_runtime.py
python build_openscr.py
python build_installer.py
```

Building the native runtime requires CMake, Visual Studio 2022 Build Tools with
Desktop C++, and a Windows SDK. `build_openscr.py` creates an `onedir` package
by default; set `OPENSCR_ONEFILE=1` to create a single executable.

## Linux

Linux builds can open, edit, and save OpenSCR projects. Preview and `.scr`
generation are Windows-only because the native runtime uses Win32 graphics and
the Windows screen-saver protocol.

## Translations and contributions

Translations are UTF-8 JSON files in [`locales`](locales). See
[`docs/TRANSLATING.md`](docs/TRANSLATING.md) to improve an existing language or
add a new one. Bug fixes, features, documentation improvements, and issue
reports are welcome at https://github.com/bjmvictor/OpenSCR.

## License

OpenSCR is developed by Benjamin Victor and distributed under the MIT License.
