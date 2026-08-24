import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from build_openscr import APP_VERSION, ROOT_DIR


VC_REDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
CHINESE_LANGUAGE_URL = "https://raw.githubusercontent.com/kira-96/Inno-Setup-Chinese-Simplified-Translation/main/ChineseSimplified.isl"
CACHE_DIR = ROOT_DIR / "installer" / "cache"
VC_REDIST = CACHE_DIR / "vc_redist.x64.exe"
CHINESE_LANGUAGE = CACHE_DIR / "ChineseSimplified.isl"
ISS_FILE = ROOT_DIR / "installer" / "OpenSCR.iss"
RELEASE_DIR = ROOT_DIR / "release"
SOURCE_DIR = RELEASE_DIR / f"OpenSCR-{APP_VERSION}-Windows-amd64-Portable"


def find_iscc():
    executable = shutil.which("ISCC.exe")
    if executable:
        return Path(executable)
    candidates = (
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
    )
    return next((path for path in candidates if path.is_file()), None)


def download_vc_runtime():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not VC_REDIST.is_file():
        print("Baixando o Microsoft Visual C++ Redistributable x64...")
        urllib.request.urlretrieve(VC_REDIST_URL, VC_REDIST)
    result = subprocess.run(
        [
            "powershell", "-NoProfile", "-Command",
            f"(Get-AuthenticodeSignature -LiteralPath '{VC_REDIST}').Status",
        ],
        check=True, capture_output=True, text=True,
    )
    if result.stdout.strip() != "Valid":
        VC_REDIST.unlink(missing_ok=True)
        raise RuntimeError("A assinatura digital do Microsoft VC++ Runtime não é válida.")

    if not CHINESE_LANGUAGE.is_file():
        print("Downloading the Simplified Chinese installer catalog...")
        urllib.request.urlretrieve(CHINESE_LANGUAGE_URL, CHINESE_LANGUAGE)


def main():
    if sys.platform != "win32":
        raise SystemExit("O instalador Windows deve ser compilado no Windows.")
    iscc = find_iscc()
    if iscc is None:
        raise SystemExit("Inno Setup 6 não encontrado. Instale-o e execute novamente.")

    environment = os.environ.copy()
    environment.pop("OPENSCR_ONEFILE", None)
    subprocess.run([sys.executable, str(ROOT_DIR / "build_openscr.py")], check=True, env=environment)
    source_dir = RELEASE_DIR / f"OpenSCR-{APP_VERSION}-Windows-amd64-Portable"
    download_vc_runtime()
    subprocess.run(
        [
            str(iscc),
            f"/DMyAppVersion={APP_VERSION}",
            f"/DSourceDir={source_dir}",
            f"/DVCRedist={VC_REDIST}",
            f"/DChineseLanguage={CHINESE_LANGUAGE}",
            f"/DOutputDir={RELEASE_DIR}",
            "/DMyMinVersion=10.0.14393",
            str(ISS_FILE),
        ],
        check=True,
    )
    print(RELEASE_DIR / f"OpenSCR-{APP_VERSION}-Windows-x64-Setup.exe")


if __name__ == "__main__":
    main()
