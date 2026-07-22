# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .conversor import converter_pdf
from .diagnostico import diagnosticar_pdf
from .lote import converter_lote_zip
from .manifesto import escrever_manifesto

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def diagnosticar(
    entrada: Path = typer.Option(..., exists=True, readable=True),
    saida: Path = typer.Option(...),
) -> None:
    """Diagnostica um PDF e grava manifesto JSON."""

    saida.mkdir(parents=True, exist_ok=True)
    diagnostico = diagnosticar_pdf(entrada)
    destino = saida / f"{entrada.stem}.diagnostico.json"
    escrever_manifesto(diagnostico, destino)
    console.print(f"[green]Diagnóstico salvo em:[/green] {destino}")


@app.command()
def converter(
    entrada: Path = typer.Option(..., exists=True, readable=True),
    saida: Path = typer.Option(...),
    dpi: int = typer.Option(300, min=150, max=600),
) -> None:
    """Converte um PDF usando extração nativa e OCR seletivo."""

    destino = converter_pdf(entrada, saida, dpi=dpi)
    console.print(f"[green]Markdown salvo em:[/green] {destino}")


@app.command("converter-lote")
def converter_lote(
    entrada: Path = typer.Option(..., exists=True, readable=True),
    saida: Path = typer.Option(...),
    dpi: int = typer.Option(300, min=150, max=600),
    documentos: int = typer.Option(
        0,
        "--documentos",
        "-n",
        min=0,
        help="Quantidade máxima de PDFs a processar; 0 processa todos.",
    ),
    retomar: bool = typer.Option(
        False,
        "--retomar/--nao-retomar",
        help="Reutiliza resultados concluídos com mesmo hash, versão e DPI.",
    ),
    remover_raiz_comum: bool = typer.Option(
        True,
        "--remover-raiz-comum/--manter-raiz-comum",
        help="Remove uma pasta-raiz única do ZIP para evitar diretórios duplicados.",
    ),
) -> None:
    """Converte PDFs de um ZIP com limite, retomada e manifesto incremental."""

    resultado = converter_lote_zip(
        entrada,
        saida,
        dpi=dpi,
        document_limit=documentos,
        resume=retomar,
        remove_common_root=remover_raiz_comum,
        progress=lambda mensagem: console.print(mensagem),
    )
    console.print(
        "[green]Lote concluído.[/green] "
        f"PDFs encontrados: {resultado.pdf_count}; "
        f"sucessos: {resultado.success_count}; "
        f"duplicados: {resultado.duplicate_count}; "
        f"falhas: {resultado.failure_count}; "
        f"não PDF ignorados: {resultado.skipped_count}; "
        f"pendentes pelo limite: {resultado.pending_count}."
    )
    console.print(
        f"[green]Manifesto do lote:[/green] {resultado.manifest_path}"
    )
    if resultado.failure_count:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()


__all__ = ["app", "console", "converter", "converter_lote", "diagnosticar"]
