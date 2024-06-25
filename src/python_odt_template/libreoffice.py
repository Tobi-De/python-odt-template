from __future__ import annotations

import abc
import logging
import platform
import subprocess
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

logger = logging.getLogger("python_odt_template")


class LibreOfficeError(Exception):
    pass


class LOConverter(abc.ABC):
    @property
    @abc.abstractmethod
    def raise_on_error(self) -> bool: ...

    @property
    @abc.abstractmethod
    def exec_bin(self) -> str: ...

    def run(self, *args) -> None:
        process = subprocess.run(
            [self.exec_bin, *args],
            check=False,
            capture_output=True,
        )
        if process.returncode != 0:
            logger.error(process.stderr.decode())
            if self.raise_on_error:
                raise LibreOfficeError(process.stderr.decode())

    @abc.abstractmethod
    def convert(self, input_file: str | Path, output_dir: str | Path, to: str = "pdf") -> None: ...


@dataclass
class LibreOffice(LOConverter):
    raise_on_error: bool = False

    @cached_property
    def exec_bin(self) -> str:
        return "/Applications/LibreOffice.app/Contents/MacOS/soffice" if platform.system() == "Darwin" else "soffice"

    def convert(self, input_file: str | Path, output_dir: str | Path, to: str = "pdf") -> None:
        self.run(
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            output_dir,
            input_file,
        )


@dataclass
class UnoConvert(LOConverter):
    host: str = "127.0.0.1"
    port: int = 2003
    raise_on_error: bool = False

    @cached_property
    def exec_bin(self) -> str:
        return "unoconvert"

    def convert(self, input_file: str | Path, output_dir: str | Path, to: str = "pdf") -> None:
        self.run(
            input_file,
            Path(output_dir) / (Path(input_file).stem + f".{to}"),
            "--convert-to",
            to,
            "--port",
            str(self.port),
            "--host",
            self.host,
        )
