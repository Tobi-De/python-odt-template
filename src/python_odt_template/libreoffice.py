from __future__ import annotations

import logging
import platform
import subprocess
from pathlib import Path

logger = logging.getLogger("python_odt_template")


__all__ = ["libreoffice", "convert_to_pdf"]


class LibreOfficeError(Exception):
    pass


def libreoffice(*args, raise_on_error=False) -> None:
    exec_name = "/Applications/LibreOffice.app/Contents/MacOS/soffice" if platform.system() == "Darwin" else "soffice"
    logger.debug("Running LibreOffice", extra=args)
    process = subprocess.run(
        [exec_name, "--headless", *args],
        check=False,
        capture_output=True,
    )
    if process.returncode != 0:
        logger.error(process.stderr.decode())
        if raise_on_error:
            raise LibreOfficeError(process.stderr.decode())


def convert_to_pdf(source_file: str | Path, output_dir: str | Path) -> None:
    if not Path(source_file).exists():
        msg = f"File not found: {source_file}"
        raise FileNotFoundError(msg)
    libreoffice("--convert-to", "pdf", "--outdir", output_dir, source_file)
