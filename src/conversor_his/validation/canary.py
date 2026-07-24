# SPDX-License-Identifier: MIT
from __future__ import annotations

import csv
import json
import re
import shutil
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

ClassificacaoOcorrencia = Literal["dispositivo_principal", "remissao"]

_PADRAO_ARTIGO = re.compile(
    r"(?P<rotulo>\bart(?:igo)?\.?)\s*"
    r"(?P<numero>\d+)"
    r"(?P<ordinal>[º°o])?"
    r"(?P<sufixo>-[A-Z])?"
    r"(?=\s|[.,;:—–-]|$)",
    re.IGNORECASE,
)

_PADRAO_PREFIXO_REMISSAO = re.compile(
    r"(?:"
    r"nos\s+termos(?:\s+d[oa])?|conforme|segundo|observad[oa]s?|"
    r"de\s+acordo\s+com|na\s+forma\s+d[oa]|dispost[oa]\s+n[oa]|"
    r"previst[oa]\s+n[oa]|referid[oa]\s+n[oa]|mencionad[oa]\s+n[oa]|"
    r"estabelecid[oa]\s+n[oa]|de\s+que\s+trata|"
    r"altera(?:-se)?(?:\s+a)?\s+redacao\s+d[oa]|"
    r"revoga(?:-se)?|acrescenta(?:-se)?|substitui(?:-se)?"
    r")\s*[\"'“”]*$",
    re.IGNORECASE,
)

_PADRAO_SUFIXO_REMISSAO = re.compile(
    r"^\s*(?:,\s*)?(?:"
    r"d[oa]s?|dest[ae]s?|destes?|daquel[ae]s?|"
    r"ao\s+(?:o\s+)?art(?:igo)?\.?|e\s+(?:o\s+)?art(?:igo)?\.?"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class OcorrenciaArtigo:
    identificador: str
    texto_original: str
    classificacao: ClassificacaoOcorrencia
    inicio: int
    fim: int


@dataclass(frozen=True, slots=True)
class ResultadoCanario:
    identificador_caso: str
    dispositivos_ausentes: list[str]
    dispositivos_inesperados: list[str]
    remissoes_encontradas: list[str]
    termos_criticos_exatos: list[str]
    termos_criticos_normalizados: list[str]
    termos_criticos_ausentes: list[str]
    aprovado: bool

    @property
    def case_id(self) -> str:
        return self.identificador_caso

    @property
    def missing_headings(self) -> list[str]:
        return self.dispositivos_ausentes

    @property
    def unexpected_headings(self) -> list[str]:
        return self.dispositivos_inesperados

    @property
    def critical_terms_missing(self) -> list[str]:
        return self.termos_criticos_ausentes

    @property
    def passed(self) -> bool:
        return self.aprovado


def normalizar_identificador_artigo(valor: str) -> str:
    texto = unicodedata.normalize("NFKC", str(valor)).upper()
    texto = re.sub(r"\s+", "", texto)
    texto = re.sub(r"^ARTIGO", "", texto)
    texto = re.sub(r"^ART\.?", "", texto)
    texto = re.sub(r"(?<=\d)[Oº°](?=-|$)", "", texto)
    texto = re.sub(r"(?<=\d)-?([A-Z])$", r"-\1", texto)
    return texto


def normalizar_texto_legal(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKC", texto)
    normalizado = normalizado.replace("\u00a0", " ").casefold()
    normalizado = re.sub(r"[‐‑‒–—]", "-", normalizado)
    normalizado = re.sub(
        r"\bart(?:igo)?\.?\s*(\d+)\s*[oº°]?(?:\s*-\s*([a-z]))?",
        lambda item: (
            f"art.{item.group(1)}"
            + (f"-{item.group(2)}" if item.group(2) else "")
        ),
        normalizado,
    )
    normalizado = re.sub(r"\blei\s*n\s*[oº°]\s*", "lei nº ", normalizado)
    normalizado = re.sub(r"\s*/\s*", "/", normalizado)
    normalizado = re.sub(r"(?<=\d)\s*%", "%", normalizado)
    normalizado = re.sub(r"(?<=\d)\s*m\s*2\b", "m2", normalizado)
    normalizado = re.sub(r"\s+", " ", normalizado)
    return normalizado.strip()


def _normalizar_contexto(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto).casefold()
    return "".join(
        caractere
        for caractere in decomposto
        if not unicodedata.combining(caractere)
    )


def _classificar_ocorrencia(
    texto: str,
    correspondencia: re.Match[str],
) -> ClassificacaoOcorrencia:
    prefixo = texto[max(0, correspondencia.start() - 100) : correspondencia.start()]
    sufixo = texto[correspondencia.end() : correspondencia.end() + 80]
    if _PADRAO_PREFIXO_REMISSAO.search(_normalizar_contexto(prefixo)):
        return "remissao"
    if _PADRAO_SUFIXO_REMISSAO.search(_normalizar_contexto(sufixo)):
        return "remissao"
    return "dispositivo_principal"


def extrair_ocorrencias_artigos(texto: str) -> list[OcorrenciaArtigo]:
    ocorrencias: list[OcorrenciaArtigo] = []
    for correspondencia in _PADRAO_ARTIGO.finditer(texto):
        numero = correspondencia.group("numero")
        sufixo = correspondencia.group("sufixo") or ""
        identificador = normalizar_identificador_artigo(f"{numero}{sufixo}")
        ocorrencias.append(
            OcorrenciaArtigo(
                identificador=identificador,
                texto_original=correspondencia.group(0),
                classificacao=_classificar_ocorrencia(texto, correspondencia),
                inicio=correspondencia.start(),
                fim=correspondencia.end(),
            )
        )
    return ocorrencias


def extrair_dispositivos_principais(texto: str) -> list[str]:
    return [
        ocorrencia.identificador
        for ocorrencia in extrair_ocorrencias_artigos(texto)
        if ocorrencia.classificacao == "dispositivo_principal"
    ]


def _valor_textual(item: Any, *chaves: str) -> str:
    if not isinstance(item, dict):
        return str(item)
    for chave in chaves:
        if chave in item:
            return str(item[chave])
    return ""


def _lista_do_caso(caso: dict[str, Any], chave_pt: str, chave_legada: str) -> list[Any]:
    valor = caso.get(chave_pt, caso.get(chave_legada, []))
    return valor if isinstance(valor, list) else []


def _contem_termo_normalizado(texto_normalizado: str, termo_normalizado: str) -> bool:
    if termo_normalizado.isdigit():
        return bool(
            re.search(
                rf"(?<!\d){re.escape(termo_normalizado)}(?!\d)",
                texto_normalizado,
            )
        )
    return termo_normalizado in texto_normalizado


def avaliar_caso(caso: dict[str, Any]) -> ResultadoCanario:
    itens_esperados = _lista_do_caso(caso, "dispositivos_esperados", "headings")
    esperados = [
        normalizar_identificador_artigo(valor)
        for item in itens_esperados
        if (valor := _valor_textual(item, "identificador", "valor", "numero")).strip()
    ]

    texto_observado = str(caso.get("texto_observado", caso.get("observed_text", "")))
    ocorrencias = extrair_ocorrencias_artigos(texto_observado)
    principais = {
        item.identificador
        for item in ocorrencias
        if item.classificacao == "dispositivo_principal"
    }
    remissoes = {
        item.identificador
        for item in ocorrencias
        if item.classificacao == "remissao"
    }

    metadados = caso.get("metadados", caso.get("metadata", {}))
    if not isinstance(metadados, dict):
        metadados = {}
    alterados = metadados.get("artigos_alterados", metadados.get("altered_articles", []))
    if not isinstance(alterados, list):
        alterados = []
    secundarios_permitidos = {
        normalizar_identificador_artigo(str(item))
        for item in alterados
        if str(item).strip()
    }
    itens_remissoes = _lista_do_caso(caso, "remissoes_esperadas", "expected_references")
    secundarios_permitidos.update(
        normalizar_identificador_artigo(valor)
        for item in itens_remissoes
        if (valor := _valor_textual(item, "identificador", "valor", "numero")).strip()
    )

    conjunto_esperado = set(esperados)
    ausentes = sorted(conjunto_esperado - principais)
    termos = [
        valor
        for item in _lista_do_caso(caso, "termos_criticos", "critical_terms")
        if (valor := _valor_textual(item, "valor", "termo", "texto")).strip()
    ]
    for termo in termos:
        correspondencia = _PADRAO_ARTIGO.fullmatch(termo.strip())
        if correspondencia:
            identificador = normalizar_identificador_artigo(
                f"{correspondencia.group('numero')}"
                f"{correspondencia.group('sufixo') or ''}"
            )
            if identificador not in conjunto_esperado:
                secundarios_permitidos.add(identificador)
    inesperados = sorted(principais - conjunto_esperado - secundarios_permitidos)
    texto_exato = texto_observado.casefold()
    texto_normalizado = normalizar_texto_legal(texto_observado)
    exatos: list[str] = []
    normalizados: list[str] = []
    ausentes_termos: list[str] = []
    for termo in termos:
        if termo.casefold() in texto_exato:
            exatos.append(termo)
            continue
        termo_normalizado = normalizar_texto_legal(termo)
        if _contem_termo_normalizado(texto_normalizado, termo_normalizado):
            normalizados.append(termo)
        else:
            ausentes_termos.append(termo)

    aprovado = not ausentes and not inesperados and not ausentes_termos
    return ResultadoCanario(
        identificador_caso=str(
            caso.get("identificador_caso", caso.get("case_id", "desconhecido"))
        ),
        dispositivos_ausentes=ausentes,
        dispositivos_inesperados=inesperados,
        remissoes_encontradas=sorted(remissoes),
        termos_criticos_exatos=exatos,
        termos_criticos_normalizados=normalizados,
        termos_criticos_ausentes=ausentes_termos,
        aprovado=aprovado,
    )


def executar_bateria_canario(
    caminho_entrada: Path,
    diretorio_saida: Path,
) -> tuple[Path, Path, bool]:
    carga = json.loads(caminho_entrada.read_text(encoding="utf-8"))
    if isinstance(carga, list):
        casos = carga
    elif isinstance(carga, dict):
        casos = carga.get("casos", carga.get("cases", []))
    else:
        casos = []
    if not isinstance(casos, list):
        raise TypeError("arquivo canário deve conter uma lista ou a chave 'casos'")

    resultados = [avaliar_caso(caso) for caso in casos]
    diretorio_saida.mkdir(parents=True, exist_ok=True)
    caminho_json = diretorio_saida / "resultados_canario.json"
    caminho_csv = diretorio_saida / "resultados_canario.csv"
    aprovado = all(resultado.aprovado for resultado in resultados)
    caminho_json.write_text(
        json.dumps(
            {
                "versao_esquema": "2.0",
                "quantidade_casos": len(resultados),
                "quantidade_aprovados": sum(resultado.aprovado for resultado in resultados),
                "quantidade_reprovados": sum(
                    not resultado.aprovado for resultado in resultados
                ),
                "aprovado": aprovado,
                "resultados": [asdict(resultado) for resultado in resultados],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    with caminho_csv.open("w", encoding="utf-8", newline="") as fluxo:
        escritor = csv.DictWriter(
            fluxo,
            fieldnames=[
                "identificador_caso",
                "aprovado",
                "dispositivos_ausentes",
                "dispositivos_inesperados",
                "remissoes_encontradas",
                "termos_criticos_exatos",
                "termos_criticos_normalizados",
                "termos_criticos_ausentes",
            ],
        )
        escritor.writeheader()
        for resultado in resultados:
            escritor.writerow(
                {
                    "identificador_caso": resultado.identificador_caso,
                    "aprovado": resultado.aprovado,
                    "dispositivos_ausentes": "|".join(resultado.dispositivos_ausentes),
                    "dispositivos_inesperados": "|".join(
                        resultado.dispositivos_inesperados
                    ),
                    "remissoes_encontradas": "|".join(resultado.remissoes_encontradas),
                    "termos_criticos_exatos": "|".join(
                        resultado.termos_criticos_exatos
                    ),
                    "termos_criticos_normalizados": "|".join(
                        resultado.termos_criticos_normalizados
                    ),
                    "termos_criticos_ausentes": "|".join(
                        resultado.termos_criticos_ausentes
                    ),
                }
            )

    caminho_json_legado = diretorio_saida / "canary_results.json"
    caminho_csv_legado = diretorio_saida / "canary_results.csv"
    shutil.copyfile(caminho_json, caminho_json_legado)
    shutil.copyfile(caminho_csv, caminho_csv_legado)
    return caminho_json, caminho_csv, aprovado


CanaryResult = ResultadoCanario
normalize_article = normalizar_identificador_artigo
extract_article_headings = extrair_dispositivos_principais
evaluate_case = avaliar_caso
run_canary_suite = executar_bateria_canario

__all__ = [
    "CanaryResult",
    "OcorrenciaArtigo",
    "ResultadoCanario",
    "avaliar_caso",
    "evaluate_case",
    "executar_bateria_canario",
    "extract_article_headings",
    "extrair_dispositivos_principais",
    "extrair_ocorrencias_artigos",
    "normalizar_identificador_artigo",
    "normalizar_texto_legal",
    "normalize_article",
    "run_canary_suite",
]
