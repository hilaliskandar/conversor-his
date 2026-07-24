import json
from pathlib import Path

from conversor_his.ocr.tesseract_engine import OcrToken
from conversor_his.reconstrucao_estrutural import (
    carregar_tokens_jsonl,
    classificar_linha,
    gravar_estrutura_ocr,
    reconstruir_blocos,
    reconstruir_linhas,
)


def token(
    text: str,
    *,
    page: int = 1,
    block: int = 1,
    paragraph: int = 1,
    line: int = 1,
    word: int = 1,
    left: int = 10,
    top: int = 10,
    width: int = 30,
    height: int = 12,
    confidence: float | None = 90.0,
) -> OcrToken:
    return OcrToken(
        text=text,
        confidence=confidence,
        page_number=page,
        block_number=block,
        paragraph_number=paragraph,
        line_number=line,
        word_number=word,
        left=left,
        top=top,
        width=width,
        height=height,
    )


def test_reconstroi_linha_e_classifica_artigo() -> None:
    tokens = [
        token("Art.", word=1, left=10),
        token("1", word=2, left=50, width=10),
        token("º", word=3, left=61, width=6),
        token("-", word=4, left=70, width=6),
        token("Regra", word=5, left=80, width=40),
    ]
    linhas = reconstruir_linhas(tokens)
    assert len(linhas) == 1
    assert linhas[0].texto == "Art. 1º - Regra"
    assert linhas[0].tipo == "artigo"
    assert linhas[0].confianca_media == 90.0


def test_classifica_unidades_juridicas_basicas() -> None:
    assert classificar_linha("TÍTULO III") == "titulo"
    assert classificar_linha("CAPÍTULO II") == "capitulo"
    assert classificar_linha("Seção I") == "secao"
    assert classificar_linha("§ 1º Regra") == "paragrafo"
    assert classificar_linha("IV - diretriz") == "inciso"
    assert classificar_linha("a) hipótese") == "alinea"


def test_detecta_duas_colunas_apenas_com_evidencia_forte() -> None:
    tokens: list[OcrToken] = []
    for indice, topo in enumerate((10, 40, 70), start=1):
        tokens.append(
            token(
                f"E{indice}",
                block=1,
                paragraph=indice,
                line=1,
                left=10,
                top=topo,
                width=80,
            )
        )
        tokens.append(
            token(
                f"D{indice}",
                block=2,
                paragraph=indice,
                line=1,
                left=310,
                top=topo,
                width=80,
            )
        )
    linhas = reconstruir_linhas(tokens)
    assert {linha.coluna for linha in linhas} == {1, 2}
    assert [linha.texto for linha in linhas if linha.coluna == 1] == ["E1", "E2", "E3"]
    assert [linha.texto for linha in linhas if linha.coluna == 2] == ["D1", "D2", "D3"]


def test_reconstroi_blocos_por_paragrafo_e_coluna() -> None:
    tokens = [
        token("Art.", line=1, word=1, left=10, top=10),
        token("1º", line=1, word=2, left=50, top=10),
        token("Texto", line=2, word=1, left=10, top=30),
    ]
    blocos = reconstruir_blocos(tokens)
    assert len(blocos) == 1
    assert blocos[0].quantidade_linhas == 2
    assert blocos[0].tipo_predominante == "artigo"
    assert blocos[0].texto == "Art. 1º\nTexto"


def test_grava_e_recarrega_estrutura_jsonl(tmp_path: Path) -> None:
    tokens = [token("Art."), token("2º", word=2, left=50)]
    origem = tmp_path / "tokens.jsonl"
    origem.write_text(
        "\n".join(json.dumps(item.to_dict(), ensure_ascii=False) for item in tokens),
        encoding="utf-8",
    )
    carregados = carregar_tokens_jsonl(origem)
    destino = gravar_estrutura_ocr(carregados, tmp_path / "estrutura.jsonl")
    registro = json.loads(destino.read_text(encoding="utf-8"))
    assert registro["tipo_registro"] == "bloco_ocr"
    assert registro["linhas"][0]["tipo"] == "artigo"
