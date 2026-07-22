# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import re
import shutil
import stat
import tempfile
import time
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from . import __version__
from .conversor import converter_pdf
from .hashing import sha256_file
from .manifesto import escrever_manifesto

_PARTE_UNIDADE_RE = re.compile(r"^[A-Za-z]:$")


@dataclass(slots=True)
class ResultadoDeConversaoEmLote:
    caminho_manifesto: Path
    quantidade