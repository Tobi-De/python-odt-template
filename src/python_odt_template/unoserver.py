# https://gist.githubusercontent.com/regebro/036da022dc7d5241a0ee97efdf1458eb/raw/find_uno.py

import glob
import os
import pathlib
import signal
import subprocess
import sys
from .libreoffice import LibreOffice


def get_uno_python():
    # Places we might find a Python install:
    possible_python_paths = []

    if os.name in ("nt", "os2"):
        if "PROGRAMFILES" in list(os.environ.keys()):
            possible_python_paths += glob.glob(
                os.environ["PROGRAMFILES"] + "\\LibreOffice*"
            )

        if "PROGRAMFILES(X86)" in list(os.environ.keys()):
            possible_python_paths += glob.glob(
                os.environ["PROGRAMFILES(X86)"] + "\\LibreOffice*"
            )

        if "PROGRAMW6432" in list(os.environ.keys()):
            possible_python_paths += glob.glob(
                os.environ["PROGRAMW6432"] + "\\LibreOffice*"
            )

    elif sys.platform == "darwin":
        possible_python_paths += ["/Applications/LibreOffice.app/Contents",
                                  "/Applications/LibreOffice.app/Resources"]
    else:
        possible_python_paths += [
            "/usr/bin",
            "/usr/local/bin",
            "~/.local/bin",
        ]
        possible_python_paths += (
                glob.glob("/usr/lib*/libreoffice*")
                + glob.glob("/opt/libreoffice*")
                + glob.glob("/usr/local/lib/libreoffice*")
                + glob.glob(os.path.expanduser("./local/lib/libreoffice*"))
        )

    found_pythons = []

    for python_path in possible_python_paths:
        path = pathlib.Path(os.path.expanduser(python_path))
        for python in path.rglob("python3"):
            if not python.is_dir() and os.access(python, os.X_OK):
                found_pythons.append(str(python))
        for python in path.rglob("python"):
            if not python.is_dir() and os.access(python, os.X_OK):
                found_pythons.append(str(python))

    pythons_with_libreoffice = []
    for python in found_pythons:
        print(f"Trying python found at {python}", end="...")
        proc = subprocess.run(
            [python, "-c", "import uno;from com.sun.star.beans import PropertyValue"],
            stderr=subprocess.PIPE,
        )
        if proc.returncode:
            print(" Failed")
        else:
            print(" Success!")
            pythons_with_libreoffice.append(python)

    return pythons_with_libreoffice


if __name__ == "__main__":
    uno_python = os.getenv("UNOSERVER_PYTHON")
    if not uno_python:
        pythons_with_libreoffice = get_uno_python()
        print(f"Found {len(pythons_with_libreoffice)} Pythons with Libreoffice libraries:")
        for index, python in enumerate(pythons_with_libreoffice):
            print(f"{index}. {python}")
        resp = input("Which one do you want to use? ")
        try:
            uno_python = pythons_with_libreoffice[int(resp)]
        except (ValueError, IndexError):
            print("Invalid selection.")
            sys.exit(1)
        print(f"Installing unoserver at {uno_python}")
        # install unoserver
        subprocess.run([uno_python, "-m", "pip", "install", "unoserver"])
        print(f"Set UNOSERVER_PYTHON={uno_python} to this installation process.")
    print(f"Using python at {uno_python}")

    try:
        process = subprocess.Popen([uno_python, "-m", "unoserver.server", "--executable", LibreOffice().exec_bin])
        process.wait()
    except KeyboardInterrupt:
        print("\nStopping the server...")
        process.send_signal(signal.SIGINT)
        process.wait()
        print("Server stopped.")
