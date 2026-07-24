from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .batch import convert_zip_batch
from .converter import convert_pdf
from .diagnostic import diagnose_pdf
from .manifest import write_manifest
from .packaging import create_analysis_zip
from .reconstrucao_estrutural import carregar_tokens_jsonl, gravar_estrutura_ocr
from .validation.canary import run_canary_suite

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


@app.command("validar-canario")
def validar_canario(
    entrada: Path = typer.Option(..., exists=True, readable=True),
    saida: Path = typer.Option(...),
) -> None:
    """Valida headings e termos críticos de uma bateria-canário JSON."""
    json_path, csv_path, passed = run_canary_suite(entrada, saida / "analise")
    console.print(f"[green]Relatório JSON:[/green] {json_path}")
    console.print(f"[green]Relatório CSV:[/green] {csv_path}")
    if not passed:
        console.print("[red]Gate canário reprovado.[/red]")
        raise typer.Exit(code=1)
    console.print("[green]Gate canário aprovado.[/green]")


@app.command("reconstruir-estrutura")
def reconstruir_estrutura(
    entrada: Path = typer.Option(..., exists=True, readable=True),
    saida: Path = typer.Option(...),
) -> None:
    """Reconstrói linhas e blocos a partir de tokens OCR posicionais."""
    tokens = carregar_tokens_jsonl(entrada)
    destino = gravar_estrutura_ocr(tokens, saida)
    console.print(f"[green]Estrutura OCR salva em:[/green] {destino}")


@app.command("empacotar-analise")
def empacotar_analise(
    entrada: Path = typer.Option(..., exists=True, file_okay=False),
    saida: Path = typer.Option(...),
) -> None:
    """Cria ZIP leve com Markdown, CSV, JSON e JSONL, sem imagens."""
    destino = create_analysis_zip(entrada, saida)
    console.print(f"[green]Pacote leve salvo em:[/green] {destino}")


if __name__ == "__main__":
    app()
