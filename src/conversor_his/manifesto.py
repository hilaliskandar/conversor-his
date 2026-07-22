# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _preparar_para_json(valor: Any) -> Any:
    if is_dataclass(valor):
        return _preparar_para_json(asdict(valor))
    if isinstance(valor, Path):
        return str(valor)
    if isinstance(valor, dict):
        return {chave: _preparar_para_json(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_preparar_para_json(item) for item in valor]
    return valor


def escrever_manifesto(conteudo: Any, caminho_saida: Path) -> None:
    """Escreve o manifesto em JSON de forma atômica."""

    dados = _preparar_para_json(conteudo)
    agora = datetime.now(timezone.utc).isoformat()
    if isinstance(dados, dict):
        dados.setdefault("generated_at", agora)
        dados["updated_at"] = agora

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    caminho_temporario = caminho_saida.with_suffix(caminho_saida.suffix + ".tmp")
    caminho_temporario.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    caminho_temporario.replace(caminho_saida)


__all__ = ["escrever_manifesto"]
