from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .batch import convert_zip_batch
from .converter import convert_pdf
from .diagnostic import diagnose_pdf
from .manifest import write_manifest

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def diagnosticar(
    entrada: Path = typer.Option(..., exists=True, readable=True),
    saida: Path = typer.Option(...),
) -> None:
    """Diagnostica um PDF e grava manifesto JSON."""
    saida.mkdir(parents=True, exist_ok=True)
    diagnosis = diagnose_pdf(entrada)
    target = saida / f"{entrada.stem}.diagnostico.json"
    write_manifest(diagnosis, target)
    console.print(f"[green]Diagnóstico salvo em:[/green] {target}")


@app.command()
def converter(
    entrada: Path = typer.Option(..., exists=True, readable=True),
    saida: Path = typer.Option(...),
    dpi: int = typer.Option(300, min=150, max=600),
) -> None:
    """Converte um PDF usando extração nativa e OCR seletivo."""
    target = convert_pdf(entrada, saida, dpi=dpi)
    console.print(f"[green]Markdown salvo em:[/green] {target}")


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
    result = convert_zip_batch(
        entrada,
        saida,
        dpi=dpi,
        document_limit=documentos,
        resume=retomar,
        remove_common_root=remover_raiz_comum,
        progress=lambda message: console.print(message),
    )
    console.print(
        "[green]Lote concluído.[/green] "
        f"PDFs encontrados: {result.pdf_count}; sucessos: {result.success_count}; "
        f"duplicados: {result.duplicate_count}; falhas: {result.failure_count}; "
        f"não PDF ignorados: {result.skipped_count}; pendentes pelo limite: {result.pending_count}."
    )
    console.print(f"[green]Manifesto do lote:[/green] {result.manifest_path}")
    if result.failure_count:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
