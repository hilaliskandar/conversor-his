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
    quantidade_pdfs: int
    quantidade_sucessos: int
    quantidade_falhas: int
    quantidade_ignorados: int
    quantidade_duplicados: int = 0
    quantidade_pendentes: int = 0

    @property
    def manifest_path(self) -> Path:
        return self.caminho_manifesto

    @property
    def pdf_count(self) -> int:
        return self.quantidade_pdfs

    @property
    def success_count(self) -> int:
        return self.quantidade_sucessos

    @property
    def failure_count(self) -> int:
        return self.quantidade_falhas

    @property
    def skipped_count(self) -> int:
        return self.quantidade_ignorados

    @property
    def duplicate_count(self) -> int:
        return self.quantidade_duplicados

    @property
    def pending_count(self) -> int:
        return self.quantidade_pendentes


def _caminho_seguro_do_membro(nome_membro: str) -> PurePosixPath:
    nome_normalizado = nome_membro.replace("\\", "/")
    caminho_membro = PurePosixPath(nome_normalizado)

    if caminho_membro.is_absolute():
        raise ValueError("caminho absoluto nao permitido")
    if not caminho_membro.parts:
        raise ValueError("caminho vazio")
    if any(parte in {"", ".", ".."} for parte in caminho_membro.parts):
        raise ValueError("caminho relativo inseguro")
    if _PARTE_UNIDADE_RE.match(caminho_membro.parts[0]):
        raise ValueError("unidade de disco nao permitida")

    return caminho_membro


def _e_link_simbolico(informacao: zipfile.ZipInfo) -> bool:
    modo = informacao.external_attr >> 16
    return stat.S_IFMT(modo) == stat.S_IFLNK


def _extrair_membro_pdf(
    arquivo_zip: zipfile.ZipFile,
    informacao: zipfile.ZipInfo,
    caminho_relativo: PurePosixPath,
    raiz_temporaria: Path,
) -> Path:
    caminho_temporario = raiz_temporaria.joinpath(*caminho_relativo.parts)
    caminho_temporario.parent.mkdir(parents=True, exist_ok=True)

    with (
        arquivo_zip.open(informacao, "r") as origem,
        caminho_temporario.open("wb") as destino,
    ):
        shutil.copyfileobj(origem, destino, length=1024 * 1024)

    with caminho_temporario.open("rb") as arquivo_pdf:
        cabecalho = arquivo_pdf.read(1024)
    if b"%PDF-" not in cabecalho:
        caminho_temporario.unlink(missing_ok=True)
        raise ValueError("arquivo com extensao PDF sem assinatura PDF valida")

    return caminho_temporario


def _raiz_comum(caminhos: list[PurePosixPath]) -> str | None:
    if not caminhos:
        return None
    primeiras_partes = {
        caminho.parts[0].casefold()
        for caminho in caminhos
        if len(caminho.parts) > 1
    }
    if len(primeiras_partes) != 1 or any(
        len(caminho.parts) == 1 for caminho in caminhos
    ):
        return None
    return caminhos[0].parts[0]


def _remover_raiz(caminho: PurePosixPath, raiz: str | None) -> PurePosixPath:
    if raiz and caminho.parts and caminho.parts[0].casefold() == raiz.casefold():
        return PurePosixPath(*caminho.parts[1:])
    return caminho


def _carregar_entradas_existentes(
    caminho_manifesto: Path,
) -> dict[str, dict[str, object]]:
    if not caminho_manifesto.exists():
        return {}
    try:
        dados = json.loads(caminho_manifesto.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    entradas = dados.get("entries", [])
    if not isinstance(entradas, list):
        return {}
    return {
        str(entrada.get("member")): entrada
        for entrada in entradas
        if isinstance(entrada, dict) and entrada.get("member")
    }


def _entrada_concluida(
    entrada: dict[str, object] | None,
    hash_origem: str,
    dpi: int,
) -> bool:
    if not entrada or entrada.get("status") not in {"success", "duplicate"}:
        return False
    if entrada.get("source_sha256") != hash_origem:
        return False
    if entrada.get("dpi") != dpi or entrada.get("converter_version") != __version__:
        return False
    if entrada.get("status") == "duplicate":
        return True
    caminho_markdown = Path(str(entrada.get("markdown_path", "")))
    caminho_manifesto = Path(str(entrada.get("manifest_path", "")))
    return caminho_markdown.exists() and caminho_manifesto.exists()


def converter_lote_zip(
    caminho_zip: Path,
    diretorio_saida: Path,
    dpi: int = 300,
    limite_documentos: int = 0,
    retomar: bool = False,
    remover_raiz_comum: bool = True,
    progresso: Callable[[str], None] | None = None,
    *,
    conversor_pdf: Callable[..., Path] | None = None,
) -> ResultadoDeConversaoEmLote:
    """Converte PDFs de um ZIP com limite, retomada e manifesto incremental.

    As chaves persistidas no manifesto de lote permanecem em inglês durante a
    transição para a versão 0.8, permitindo retomar lotes produzidos pela API 0.7.
    """

    if limite_documentos < 0:
        raise ValueError("limite_documentos deve ser zero ou positivo")

    funcao_conversao = conversor_pdf or converter_pdf
    caminho_zip = caminho_zip.resolve()
    diretorio_saida = diretorio_saida.resolve()
    diretorio_saida.mkdir(parents=True, exist_ok=True)

    if not zipfile.is_zipfile(caminho_zip):
        raise ValueError(f"arquivo de entrada nao e um ZIP valido: {caminho_zip}")

    caminho_manifesto_lote = (
        diretorio_saida / f"{caminho_zip.stem}.lote.manifest.json"
    )
    hash_zip_origem = sha256_file(caminho_zip)
    entradas_existentes = (
        _carregar_entradas_existentes(caminho_manifesto_lote) if retomar else {}
    )

    entradas: list[dict[str, object]] = []
    entradas_ignoradas: list[dict[str, str]] = []
    caminhos_vistos: set[str] = set()
    hashes_vistos: dict[str, str] = {}
    quantidade_sucessos = 0
    quantidade_falhas = 0
    quantidade_ignorados = 0
    quantidade_duplicados = 0
    quantidade_processados = 0
    inicio_desempenho = time.perf_counter()
    iniciado_em = datetime.now(timezone.utc).isoformat()

    def emitir(mensagem: str) -> None:
        if progresso is not None:
            progresso(mensagem)

    def persistir(
        estado: str,
        quantidade_total_pdfs: int,
        quantidade_pendentes: int,
        concluido: bool = False,
    ) -> None:
        conteudo: dict[str, object] = {
            "source_zip": caminho_zip,
            "source_zip_sha256": hash_zip_origem,
            "output_directory": diretorio_saida,
            "converter_version": __version__,
            "dpi": dpi,
            "document_limit": limite_documentos,
            "resume_enabled": retomar,
            "status": estado,
            "started_at": iniciado_em,
            "pdf_count": quantidade_total_pdfs,
            "processed_count": quantidade_processados,
            "success_count": quantidade_sucessos,
            "failure_count": quantidade_falhas,
            "duplicate_count": quantidade_duplicados,
            "skipped_non_pdf_count": quantidade_ignorados,
            "pending_count": quantidade_pendentes,
            "directory_policy": "mirror_zip_structure",
            "common_root_removed": remover_raiz_comum,
            "processing_seconds": round(
                time.perf_counter() - inicio_desempenho,
                3,
            ),
            "ignored_entries": entradas_ignoradas,
            "entries": entradas,
            "generated_at": iniciado_em,
        }
        if concluido:
            conteudo["completed_at"] = datetime.now(timezone.utc).isoformat()
        escrever_manifesto(conteudo, caminho_manifesto_lote)

    quantidade_total_pdfs = 0
    quantidade_pendentes = 0
    with tempfile.TemporaryDirectory(
        prefix="conversor_his_lote_"
    ) as nome_temporario:
        raiz_temporaria = Path(nome_temporario)

        with zipfile.ZipFile(caminho_zip, "r") as arquivo_zip:
            candidatas: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
            for informacao in arquivo_zip.infolist():
                if informacao.is_dir():
                    continue
                try:
                    caminho = _caminho_seguro_do_membro(informacao.filename)
                except ValueError as erro:
                    quantidade_falhas += 1
                    entradas.append(
                        {
                            "member": informacao.filename,
                            "status": "rejected",
                            "error": str(erro),
                        }
                    )
                    continue
                if caminho.suffix.casefold() != ".pdf":
                    quantidade_ignorados += 1
                    entradas_ignoradas.append(
                        {
                            "member": caminho.as_posix(),
                            "status": "ignored",
                            "reason": "extensao diferente de PDF",
                        }
                    )
                    continue
                candidatas.append((informacao, caminho))

            candidatas.sort(key=lambda item: item[1].as_posix().casefold())
            quantidade_total_pdfs = len(candidatas)
            raiz = (
                _raiz_comum([caminho for _, caminho in candidatas])
                if remover_raiz_comum
                else None
            )
            candidatas_selecionadas = (
                candidatas
                if limite_documentos == 0
                else candidatas[:limite_documentos]
            )
            quantidade_pendentes = quantidade_total_pdfs - len(
                candidatas_selecionadas
            )
            persistir("running", quantidade_total_pdfs, quantidade_pendentes)

            for posicao, (informacao, caminho_original) in enumerate(
                candidatas_selecionadas,
                start=1,
            ):
                caminho_relativo = _remover_raiz(caminho_original, raiz)
                nome_membro = caminho_original.as_posix()
                chave_colisao = caminho_relativo.as_posix().casefold()

                if chave_colisao in caminhos_vistos:
                    quantidade_falhas += 1
                    entradas.append(
                        {
                            "member": nome_membro,
                            "output_relative_path": caminho_relativo.as_posix(),
                            "status": "failed",
                            "error": "caminho PDF duplicado no ZIP",
                        }
                    )
                    persistir(
                        "running",
                        quantidade_total_pdfs,
                        quantidade_pendentes,
                    )
                    continue
                caminhos_vistos.add(chave_colisao)

                if _e_link_simbolico(informacao):
                    quantidade_falhas += 1
                    entradas.append(
                        {
                            "member": nome_membro,
                            "status": "rejected",
                            "error": "link simbolico nao permitido no ZIP",
                        }
                    )
                    persistir(
                        "running",
                        quantidade_total_pdfs,
                        quantidade_pendentes,
                    )
                    continue

                diretorio_destino = diretorio_saida.joinpath(
                    *caminho_relativo.parent.parts
                )
                referencia_origem = f"{caminho_zip}!/{nome_membro}"
                emitir(
                    f"[{posicao}/{len(candidatas_selecionadas)}] {nome_membro}"
                )

                try:
                    pdf_temporario = _extrair_membro_pdf(
                        arquivo_zip,
                        informacao,
                        caminho_original,
                        raiz_temporaria,
                    )
                    hash_origem = sha256_file(pdf_temporario)
                    entrada_existente = entradas_existentes.get(nome_membro)
                    if retomar and _entrada_concluida(
                        entrada_existente,
                        hash_origem,
                        dpi,
                    ):
                        entrada_retomada = dict(entrada_existente)
                        entrada_retomada["status"] = "success"
                        entrada_retomada["resumed_without_processing"] = True
                        entradas.append(entrada_retomada)
                        quantidade_sucessos += 1
                        quantidade_processados += 1
                        emitir(
                            "  já concluído; reutilizado pelo modo de retomada"
                        )
                        persistir(
                            "running",
                            quantidade_total_pdfs,
                            quantidade_pendentes,
                        )
                        continue

                    duplicado_de = hashes_vistos.get(hash_origem)
                    if duplicado_de:
                        quantidade_duplicados += 1
                        quantidade_processados += 1
                        entradas.append(
                            {
                                "member": nome_membro,
                                "output_relative_path": caminho_relativo.as_posix(),
                                "status": "duplicate",
                                "duplicate_of": duplicado_de,
                                "source_sha256": hash_origem,
                                "dpi": dpi,
                                "converter_version": __version__,
                            }
                        )
                        emitir(
                            f"  duplicado exato de {duplicado_de}; "
                            "conversão dispensada"
                        )
                        persistir(
                            "running",
                            quantidade_total_pdfs,
                            quantidade_pendentes,
                        )
                        continue
                    hashes_vistos[hash_origem] = nome_membro

                    entrada_atual: dict[str, object] = {
                        "member": nome_membro,
                        "output_relative_path": caminho_relativo.as_posix(),
                        "status": "processing",
                        "source_sha256": hash_origem,
                        "output_directory": str(diretorio_destino),
                        "dpi": dpi,
                        "converter_version": __version__,
                    }
                    entradas.append(entrada_atual)
                    persistir(
                        "running",
                        quantidade_total_pdfs,
                        quantidade_pendentes,
                    )

                    inicio_documento = time.perf_counter()
                    caminho_markdown = funcao_conversao(
                        pdf_temporario,
                        diretorio_destino,
                        dpi=dpi,
                        referencia_origem=referencia_origem,
                    )
                    caminho_manifesto = (
                        diretorio_destino
                        / f"{caminho_relativo.stem}.manifest.json"
                    )
                    entrada_atual.update(
                        {
                            "status": "success",
                            "markdown_path": str(caminho_markdown),
                            "manifest_path": str(caminho_manifesto),
                            "processing_seconds": round(
                                time.perf_counter() - inicio_documento,
                                3,
                            ),
                        }
                    )
                    quantidade_sucessos += 1
                    quantidade_processados += 1
                except KeyboardInterrupt:
                    if entradas and entradas[-1].get("status") == "processing":
                        entradas[-1]["status"] = "interrupted"
                        entradas[-1]["error"] = (
                            "processamento interrompido pelo usuario"
                        )
                    persistir(
                        "interrupted",
                        quantidade_total_pdfs,
                        quantidade_pendentes,
                    )
                    raise
                except Exception as erro:  # noqa: BLE001
                    quantidade_falhas += 1
                    quantidade_processados += 1
                    if entradas and entradas[-1].get("status") == "processing":
                        entrada_atual = entradas[-1]
                    else:
                        entrada_atual = {
                            "member": nome_membro,
                            "output_relative_path": caminho_relativo.as_posix(),
                        }
                        entradas.append(entrada_atual)
                    entrada_atual.update(
                        {
                            "status": "failed",
                            "output_directory": str(diretorio_destino),
                            "error_type": type(erro).__name__,
                            "error": str(erro),
                        }
                    )
                persistir(
                    "running",
                    quantidade_total_pdfs,
                    quantidade_pendentes,
                )

    if quantidade_falhas:
        estado_final = "completed_with_failures"
    elif quantidade_pendentes:
        estado_final = "completed_with_limit"
    else:
        estado_final = "completed"
    persistir(
        estado_final,
        quantidade_total_pdfs,
        quantidade_pendentes,
        concluido=True,
    )

    return ResultadoDeConversaoEmLote(
        caminho_manifesto=caminho_manifesto_lote,
        quantidade_pdfs=quantidade_total_pdfs,
        quantidade_sucessos=quantidade_sucessos,
        quantidade_falhas=quantidade_falhas,
        quantidade_ignorados=quantidade_ignorados,
        quantidade_duplicados=quantidade_duplicados,
        quantidade_pendentes=quantidade_pendentes,
    )


__all__ = [
    "ResultadoDeConversaoEmLote",
    "converter_lote_zip",
]
