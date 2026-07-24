import json
from pathlib import Path

from conversor_his.validation.canary import (
    CanaryResult,
    ResultadoCanario,
    avaliar_caso,
    executar_bateria_canario,
    extrair_ocorrencias_artigos,
    normalizar_texto_legal,
)


def test_preserva_sufixos_e_termos() -> None:
    resultado = avaliar_caso(
        {
            "identificador_caso": "sufixos",
            "dispositivos_esperados": ["70-A", "70-B"],
            "termos_criticos": ["15%", "m²"],
            "texto_observado": "Art. 70-A taxa de 15%. Art. 70-B área de 20 m².",
        }
    )
    assert resultado.aprovado is True


def test_normaliza_artigos_ordinais_e_espacos() -> None:
    resultado = avaliar_caso(
        {
            "identificador_caso": "C03",
            "dispositivos_esperados": ["Art.103", "Art. 105", "Art.108"],
            "termos_criticos": ["Art.103", "Art.105", "Art.108"],
            "texto_observado": "Art.103 — A. Art. 105 — B. Art. 108 — C.",
        }
    )
    assert resultado.aprovado is True
    assert resultado.termos_criticos_normalizados == ["Art.105", "Art.108"]


def test_artigo_por_extenso_e_lei_sem_espaco_sao_normalizados() -> None:
    resultado = avaliar_caso(
        {
            "identificador_caso": "C07",
            "dispositivos_esperados": ["1"],
            "termos_criticos": ["LEI Nº 1.340/2018", "Artigo 1º", "250m²"],
            "texto_observado": (
                "LEINº 1.340/2018. Artigo 1º - Fica alterada a norma, "
                "com área não inferior a 250m?."
            ),
        }
    )
    assert resultado.dispositivos_ausentes == []
    assert resultado.termos_criticos_normalizados == ["LEI Nº 1.340/2018"]
    assert resultado.termos_criticos_ausentes == ["250m²"]
    assert resultado.aprovado is False


def test_distingue_dispositivo_principal_de_remissao() -> None:
    texto = (
        "Art. 74. O Município observará o disposto no art. 12 da Lei Federal "
        "e no artigo 15 deste Código."
    )
    ocorrencias = extrair_ocorrencias_artigos(texto)
    assert [(item.identificador, item.classificacao) for item in ocorrencias] == [
        ("74", "dispositivo_principal"),
        ("12", "remissao"),
        ("15", "remissao"),
    ]


def test_artigos_alterados_nao_sao_dispositivos_inesperados() -> None:
    resultado = avaliar_caso(
        {
            "case_id": "C07",
            "headings": ["1"],
            "critical_terms": ["Artigo 1º"],
            "observed_text": (
                "Altera a redação do Artigo 82. Artigo 1º - O Artigo 82 passa "
                "a vigorar. Artigo 110 — São diretrizes para a ZBD."
            ),
            "metadata": {"altered_articles": ["82", "110"]},
        }
    )
    assert resultado.dispositivos_inesperados == []
    assert resultado.aprovado is True


def test_mantem_erro_ocr_critico_como_reprovacao() -> None:
    resultado = avaliar_caso(
        {
            "case_id": "C04",
            "headings": ["126", "127"],
            "critical_terms": ["Art.126"],
            "observed_text": "Aft.126 — Revogam-se. Art.127 — Extinguem-se.",
        }
    )
    assert resultado.dispositivos_ausentes == ["126"]
    assert resultado.termos_criticos_ausentes == ["Art.126"]
    assert resultado.aprovado is False


def test_api_legada_permanece_disponivel() -> None:
    resultado = CanaryResult(
        identificador_caso="compatibilidade",
        dispositivos_ausentes=[],
        dispositivos_inesperados=[],
        remissoes_encontradas=[],
        termos_criticos_exatos=[],
        termos_criticos_normalizados=[],
        termos_criticos_ausentes=[],
        aprovado=True,
    )
    assert isinstance(resultado, ResultadoCanario)
    assert resultado.case_id == "compatibilidade"
    assert resultado.passed is True


def test_bateria_grava_nomes_ptbr_e_aliases_legados(tmp_path: Path) -> None:
    origem = tmp_path / "casos.json"
    origem.write_text(
        json.dumps(
            {
                "casos": [
                    {
                        "identificador_caso": "simples",
                        "dispositivos_esperados": ["1º"],
                        "termos_criticos": ["Art. 1º"],
                        "texto_observado": "Art. 1º - Fica instituído.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    caminho_json, caminho_csv, aprovado = executar_bateria_canario(
        origem, tmp_path / "analise"
    )
    assert aprovado is True
    assert caminho_json.name == "resultados_canario.json"
    assert caminho_csv.name == "resultados_canario.csv"
    assert (tmp_path / "analise" / "canary_results.json").exists()
    assert (tmp_path / "analise" / "canary_results.csv").exists()


def test_normalizacao_controlada_nao_corrige_corrupcao() -> None:
    assert normalizar_texto_legal("Art. 105") == "art.105"
    assert normalizar_texto_legal("250m²") == "250m2"
    assert normalizar_texto_legal("250m?") == "250m?"
    assert normalizar_texto_legal("TÍTULO III") != normalizar_texto_legal("TÍTULO ll")


def test_artigos_ordinais_sem_espaco_nao_mascaram_titulo_corrompido() -> None:
    resultado = avaliar_caso(
        {
            "identificador_caso": "C01",
            "dispositivos_esperados": ["5", "6", "7", "8"],
            "termos_criticos": ["Art.5º", "Art.8º", "TÍTULO III"],
            "texto_observado": (
                "Art.5º - A propriedade. Art.6º - Sustentabilidade. "
                "Art.7º - A gestão. TÍTULO Dos instrumentos. Art8º - Para a promoção."
            ),
        }
    )
    assert resultado.dispositivos_ausentes == []
    assert resultado.termos_criticos_normalizados == ["Art.8º"]
    assert resultado.termos_criticos_ausentes == ["TÍTULO III"]
    assert resultado.aprovado is False


def test_bateria_aceita_lista_na_raiz(tmp_path: Path) -> None:
    origem = tmp_path / "lista.json"
    origem.write_text(
        json.dumps(
            [
                {
                    "case_id": "lista",
                    "headings": ["1"],
                    "critical_terms": ["Art.1º"],
                    "observed_text": "Art.1º - Regra.",
                }
            ]
        ),
        encoding="utf-8",
    )
    _, _, aprovado = executar_bateria_canario(origem, tmp_path / "saida")
    assert aprovado is True


def test_normaliza_ordinal_com_sufixo() -> None:
    resultado = avaliar_caso(
        {
            "identificador_caso": "ordinal-sufixo",
            "dispositivos_esperados": ["1º-A"],
            "texto_observado": "Art. 1º-A. Regra complementar.",
        }
    )
    assert resultado.aprovado is True
