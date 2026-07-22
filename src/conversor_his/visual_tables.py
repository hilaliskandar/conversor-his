# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from .tabelas import AvaliacaoDeTabela

_COMPRIMENTO_HORIZONTAL_MINIMO = 20.0
_ESPESSURA_LINHA_MAXIMA = 2.5
_COMPRIMENTO_VERTICAL_MINIMO = 8.0

_MARCADORES_LEGAIS = {
    "lei": re.compile(r"\bLEI\s+(?:N|NO|NUMERO)\b"),
    "artigo": re.compile(r"\bART\.?\s*\d+"),
    "prefeito": re.compile(r"\bPREFEIT[OA]\b"),
    "camara": re.compile(r"\bCAMARA\s+MUNICIPAL\b"),
    "sancao": re.compile(r"\bSANCIONA\b"),
    "vigencia": re.compile(r"\bENTRARA?\s+EM\s+VIGOR\b"),
    "revogacao": re.compile(r"\bREVOGAD[AO]S?\b"),
    "providencias": re.compile(r"\bPROVIDENCIAS\b"),
}


@dataclass(slots=True)
class EvidenciaDeGradeVisual:
    detectada: bool
    forte: bool
    pontuacao: int
    quantidade_retangulos: int
    linhas_horizontais: int
    linhas_verticais: int
    motivos: list[str] = field(default_factory=list)

    @property
    def detected(self) -> bool:
        return self.detectada

    @property
    def strong(self) -> bool:
        return self.forte

    @property
    def score(self) -> int:
        return self.pontuacao

    @property
    def rectangle_count(self) -> int:
        return self.quantidade_retangulos

    @property
    def horizontal_lines(self) -> int:
        return self.linhas_horizontais

    @property
    def vertical_lines(self) -> int:
        return self.linhas_verticais

    @property
    def reasons(self) -> list[str]:
        return self.motivos


VisualGridEvidence = EvidenciaDeGradeVisual


def _maiusculas_sem_acentos(texto: str) -> str:
    texto_decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(
        caractere
        for caractere in texto_decomposto
        if not unicodedata.combining(caractere)
    ).upper()


def avaliar_grade_vetorial(pagina: Any) -> EvidenciaDeGradeVisual:
    """Obtém evidência de grade diretamente das operações vetoriais do PDF."""

    quantidade_retangulos = 0
    linhas_horizontais = 0
    linhas_verticais = 0
    motivos: list[str] = []

    try:
        conteudos = pagina.get_contents()
        operacoes = [] if conteudos is None else getattr(conteudos, "operations", [])
        for operandos, operador in operacoes:
            if operador != b"re" or len(operandos) < 4:
                continue
            try:
                _, _, largura, altura = (
                    float(valor) for valor in operandos[:4]
                )
            except (TypeError, ValueError):
                continue

            quantidade_retangulos += 1
            largura_absoluta = abs(largura)
            altura_absoluta = abs(altura)
            if (
                altura_absoluta <= _ESPESSURA_LINHA_MAXIMA
                and largura_absoluta >= _COMPRIMENTO_HORIZONTAL_MINIMO
            ):
                linhas_horizontais += 1
            if (
                largura_absoluta <= _ESPESSURA_LINHA_MAXIMA
                and altura_absoluta >= _COMPRIMENTO_VERTICAL_MINIMO
            ):
                linhas_verticais += 1
    except Exception as erro:  # pragma: no cover - PDF corrompido ou backend incomum
        return EvidenciaDeGradeVisual(
            detectada=False,
            forte=False,
            pontuacao=0,
            quantidade_retangulos=quantidade_retangulos,
            linhas_horizontais=linhas_horizontais,
            linhas_verticais=linhas_verticais,
            motivos=[f"evidencia vetorial indisponivel: {type(erro).__name__}"],
        )

    detectada = (
        quantidade_retangulos >= 10
        and linhas_horizontais >= 4
        and linhas_verticais >= 3
    )
    forte = (
        quantidade_retangulos >= 16
        and linhas_horizontais >= 8
        and linhas_verticais >= 6
    )

    pontuacao = 0
    if detectada:
        pontuacao += 3
        motivos.append("grade vetorial com linhas horizontais e verticais")
    if forte:
        pontuacao += 3
        motivos.append("grade vetorial forte e repetitiva")
    pontuacao += min(linhas_horizontais, 20) // 4
    pontuacao += min(linhas_verticais, 20) // 3

    return EvidenciaDeGradeVisual(
        detectada=detectada,
        forte=forte,
        pontuacao=pontuacao,
        quantidade_retangulos=quantidade_retangulos,
        linhas_horizontais=linhas_horizontais,
        linhas_verticais=linhas_verticais,
        motivos=motivos,
    )


def _contar_marcadores_legais(texto: str) -> int:
    texto_normalizado = _maiusculas_sem_acentos(texto)
    return sum(
        bool(padrao.search(texto_normalizado))
        for padrao in _MARCADORES_LEGAIS.values()
    )


def combinar_evidencia_visual_de_tabela(
    avaliacao: AvaliacaoDeTabela,
    evidencia: EvidenciaDeGradeVisual,
    texto_bruto: str,
) -> AvaliacaoDeTabela:
    """Combina evidência textual e vetorial sem forçar certeza indevida."""

    avaliacao.grade_visual_detectada = evidencia.detectada
    avaliacao.grade_visual_forte = evidencia.forte
    avaliacao.pontuacao_grade_visual = evidencia.pontuacao
    avaliacao.quantidade_retangulos_vetoriais = evidencia.quantidade_retangulos
    avaliacao.linhas_vetoriais_horizontais = evidencia.linhas_horizontais
    avaliacao.linhas_vetoriais_verticais = evidencia.linhas_verticais

    for motivo in evidencia.motivos:
        if motivo not in avaliacao.motivos:
            avaliacao.motivos.append(motivo)

    if evidencia.detectada and avaliacao.classificacao == "not_table":
        avaliacao.classificacao = "visual_candidate"
        avaliacao.suspeita = False
        avaliacao.pontuacao += evidencia.pontuacao
        avaliacao.perfil_conteudo = "visual_grid"
        return avaliacao

    tem_titulo_explicito = any(
        "titulo tabular" in motivo for motivo in avaliacao.motivos
    )
    prosa_legal = (
        avaliacao.classificacao == "candidate"
        and avaliacao.perfil_conteudo == "generic_table"
        and avaliacao.proporcao_lista_legal >= 0.20
        and len(avaliacao.ocorrencias_cabecalho) <= 2
        and not tem_titulo_explicito
        and _contar_marcadores_legais(texto_bruto) >= 3
    )
    if not evidencia.detectada and prosa_legal:
        avaliacao.classificacao = "not_table"
        avaliacao.suspeita = False
        avaliacao.motivos.append(
            "reclassificada como prosa juridica: sem grade vetorial e com marcadores legais"
        )
        avaliacao.perfil_conteudo = "legal_amendment"

    return avaliacao


def assess_vector_grid(page: Any) -> EvidenciaDeGradeVisual:
    """Preserva a assinatura pública da versão 0.7."""
    return avaliar_grade_vetorial(page)


def merge_visual_table_evidence(
    assessment: AvaliacaoDeTabela,
    evidence: EvidenciaDeGradeVisual,
    raw_text: str,
) -> AvaliacaoDeTabela:
    """Preserva a assinatura pública da versão 0.7."""
    return combinar_evidencia_visual_de_tabela(assessment, evidence, raw_text)


__all__ = [
    "EvidenciaDeGradeVisual",
    "VisualGridEvidence",
    "assess_vector_grid",
    "avaliar_grade_vetorial",
    "combinar_evidencia_visual_de_tabela",
    "merge_visual_table_evidence",
]
