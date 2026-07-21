from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

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
    """Converte PDF usando extração nativa e OCR seletivo."""
    target = convert_pdf(entrada, saida, dpi=dpi)
    console.print(f"[green]Markdown salvo em:[/green] {target}")


if __name__ == "__main__":
    app()
